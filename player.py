#!/usr/bin/env python3
"""Kids QR-Code Media Player - main orchestrator."""

import argparse
import asyncio
import logging
import signal
import subprocess
import sys
import time
from pathlib import Path

import mpv_control
import scanner
import splash
from config import (
    COMMAND_PREFIX,
    COMMANDS,
    IDLE_POLL_SECONDS,
    MEDIA_DIR,
    MPV_CMD,
    MPV_SOCKET,
    SCAN_DEBOUNCE_SECONDS,
    SEEK_STEP,
    VIDEO_EXTENSIONS,
    VOLUME_STEP,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
log = logging.getLogger("player")

# Track last scan for debounce
_last_scan_text = ""
_last_scan_time = 0.0

# Flag to signal shutdown
_shutting_down = False


def find_video(stem: str) -> Path | None:
    """Find a video file in MEDIA_DIR matching the given stem (case-insensitive)."""
    stem_lower = stem.lower()
    for f in MEDIA_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS and f.stem.lower() == stem_lower:
            return f
    return None


def show_splash() -> None:
    """Generate and load the splash screen (with current time) in mpv."""
    path = splash.generate()
    mpv_control.load_file(path)
    log.info("Showing splash screen")


async def handle_scan(text: str) -> None:
    """Process a scanned QR code text."""
    global _last_scan_text, _last_scan_time, _shutting_down

    now = time.monotonic()

    # Debounce duplicate scans
    if text == _last_scan_text and (now - _last_scan_time) < SCAN_DEBOUNCE_SECONDS:
        log.debug("Debounced duplicate scan: %s", text)
        return
    _last_scan_text = text
    _last_scan_time = now

    # Security: reject path traversal attempts
    if "/" in text or ".." in text:
        log.warning("Rejected suspicious scan input: %s", text)
        return

    text_upper = text.upper()

    # Handle commands
    if text_upper.startswith(COMMAND_PREFIX):
        cmd = text_upper[len(COMMAND_PREFIX):]
        if cmd not in COMMANDS:
            log.warning("Unknown command: %s", cmd)
            return
        log.info("Executing command: %s", cmd)
        _execute_command(cmd)
        return

    # Handle video file lookup
    video = find_video(text)
    if video is None:
        log.warning("No video found for: %s", text)
        return

    log.info("Playing: %s", video)
    mpv_control.load_file(str(video))


def _execute_command(cmd: str) -> None:
    """Execute a CMD: command."""
    global _shutting_down

    if cmd == "PAUSE":
        mpv_control.pause_toggle()
    elif cmd == "STOP":
        mpv_control.stop()
        show_splash()
    elif cmd == "VOLUP":
        mpv_control.volume_up(VOLUME_STEP)
    elif cmd == "VOLDOWN":
        mpv_control.volume_down(VOLUME_STEP)
    elif cmd == "MUTE":
        mpv_control.mute_toggle()
    elif cmd == "FWD":
        mpv_control.seek(SEEK_STEP)
    elif cmd == "RWD":
        mpv_control.seek(-SEEK_STEP)
    elif cmd == "EXIT":
        log.info("EXIT command received, shutting down")
        _shutting_down = True


async def idle_watcher() -> None:
    """Poll mpv and reload splash when playback ends. Refreshes clock every minute."""
    splash_showing = False
    last_minute = -1
    while not _shutting_down:
        await asyncio.sleep(IDLE_POLL_SECONDS)
        if mpv_control.is_idle():
            from datetime import datetime
            current_minute = datetime.now().minute
            if not splash_showing or current_minute != last_minute:
                show_splash()
                splash_showing = True
                last_minute = current_minute
        else:
            splash_showing = False
            last_minute = -1


async def _mpv_watcher(mpv_proc: subprocess.Popen) -> None:
    """Watch for mpv process exit (e.g. Alt+F4, Q, ESC) and trigger shutdown."""
    global _shutting_down
    while not _shutting_down:
        if mpv_proc.poll() is not None:
            log.info("mpv exited (code %s), shutting down", mpv_proc.returncode)
            _shutting_down = True
            return
        await asyncio.sleep(0.5)


async def shutdown_watcher() -> None:
    """Watch for the shutdown flag and cancel all tasks."""
    while not _shutting_down:
        await asyncio.sleep(0.5)
    log.info("Shutdown requested, stopping...")


async def run() -> None:
    """Main entry point: start mpv, scanner loop, idle watcher."""
    global _shutting_down

    # Ensure media directory exists
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    # Clean up stale socket
    socket_path = Path(MPV_SOCKET)
    if socket_path.exists():
        socket_path.unlink()

    # Launch mpv subprocess
    log.info("Starting mpv...")
    mpv_proc = subprocess.Popen(MPV_CMD)

    # Give mpv a moment to create the socket
    for _ in range(20):
        if socket_path.exists():
            break
        await asyncio.sleep(0.25)
    else:
        log.error("mpv socket did not appear, exiting")
        mpv_proc.terminate()
        return

    log.info("mpv is ready")
    show_splash()

    # Set up signal handlers for clean shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: _signal_shutdown())

    # Run input reader(s), idle watcher, and mpv process monitor concurrently
    tasks = [
        asyncio.create_task(idle_watcher()),
        asyncio.create_task(shutdown_watcher()),
        asyncio.create_task(_mpv_watcher(mpv_proc)),
        asyncio.create_task(_keyboard_exit_watcher()),
    ]
    if _keyboard_mode:
        tasks.append(asyncio.create_task(_keyboard_reader()))
    else:
        tasks.append(asyncio.create_task(scanner.read_scans(handle_scan)))

    # Wait until shutdown is requested or a task fails
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    # Cancel remaining tasks
    for t in pending:
        t.cancel()
    for t in pending:
        try:
            await t
        except asyncio.CancelledError:
            pass

    # Shut down mpv (if still running)
    if mpv_proc.poll() is None:
        log.info("Terminating mpv...")
        mpv_proc.terminate()
        try:
            mpv_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            mpv_proc.kill()

    log.info("Goodbye!")


async def _keyboard_exit_watcher() -> None:
    """Monitor physical keyboards (not the scanner) for Q/ESC to exit.

    Uses evdev to read directly from input devices, bypassing the window
    manager entirely - no focus needed.
    """
    global _shutting_down
    from evdev import InputDevice, categorize, ecodes, list_devices
    from config import SCANNER_DEVICE_NAME

    EXIT_KEYS = {ecodes.KEY_Q, ecodes.KEY_ESC}

    while not _shutting_down:
        # Find keyboard devices that are NOT the scanner
        keyboards = []
        for path in list_devices():
            dev = InputDevice(path)
            if SCANNER_DEVICE_NAME in dev.name:
                continue
            caps = dev.capabilities(verbose=False)
            # Check if device has EV_KEY with common keyboard keys
            if ecodes.EV_KEY in caps and ecodes.KEY_Q in caps[ecodes.EV_KEY]:
                keyboards.append(dev)

        if not keyboards:
            await asyncio.sleep(3)
            continue

        log.info("Watching %d keyboard(s) for Q/ESC exit", len(keyboards))
        try:
            await _monitor_keyboards(keyboards, EXIT_KEYS)
        except OSError:
            log.debug("Keyboard disconnected, will rescan...")
            await asyncio.sleep(3)


async def _monitor_keyboards(keyboards, exit_keys) -> None:
    """Read from multiple keyboards, trigger shutdown on exit keys."""
    global _shutting_down
    from evdev import ecodes

    async def _watch_one(dev):
        global _shutting_down
        async for event in dev.async_read_loop():
            if _shutting_down:
                return
            if event.type == ecodes.EV_KEY and event.value == 1:  # key down
                if event.code in exit_keys:
                    log.info("Exit key pressed on keyboard, shutting down")
                    _shutting_down = True
                    return

    tasks = [asyncio.create_task(_watch_one(kb)) for kb in keyboards]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()


async def _keyboard_reader() -> None:
    """Read lines from stdin as simulated scans (for testing without a scanner)."""
    log.info("Keyboard mode: type QR code text and press Enter")
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
    while not _shutting_down:
        line = await reader.readline()
        if not line:
            break
        text = line.decode().strip()
        if text:
            await handle_scan(text)


def _signal_shutdown() -> None:
    global _shutting_down
    _shutting_down = True


_keyboard_mode = False


def main() -> None:
    global _keyboard_mode
    parser = argparse.ArgumentParser(description="Kids QR-Code Media Player")
    parser.add_argument(
        "--keyboard", action="store_true",
        help="Read scan input from stdin instead of USB scanner (for testing)",
    )
    args = parser.parse_args()
    _keyboard_mode = args.keyboard

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
