"""evdev USB barcode/QR scanner reader with async yields."""

import asyncio
import logging
from evdev import InputDevice, categorize, ecodes, list_devices

from config import SCANNER_DEVICE_NAME, SCANNER_RECONNECT_SECONDS

log = logging.getLogger(__name__)

# US keyboard keycode → (normal, shifted) character mapping
KEYMAP = {
    ecodes.KEY_1: ("1", "!"),
    ecodes.KEY_2: ("2", "@"),
    ecodes.KEY_3: ("3", "#"),
    ecodes.KEY_4: ("4", "$"),
    ecodes.KEY_5: ("5", "%"),
    ecodes.KEY_6: ("6", "^"),
    ecodes.KEY_7: ("7", "&"),
    ecodes.KEY_8: ("8", "*"),
    ecodes.KEY_9: ("9", "("),
    ecodes.KEY_0: ("0", ")"),
    ecodes.KEY_MINUS: ("-", "_"),
    ecodes.KEY_EQUAL: ("=", "+"),
    ecodes.KEY_Q: ("q", "Q"),
    ecodes.KEY_W: ("w", "W"),
    ecodes.KEY_E: ("e", "E"),
    ecodes.KEY_R: ("r", "R"),
    ecodes.KEY_T: ("t", "T"),
    ecodes.KEY_Y: ("y", "Y"),
    ecodes.KEY_U: ("u", "U"),
    ecodes.KEY_I: ("i", "I"),
    ecodes.KEY_O: ("o", "O"),
    ecodes.KEY_P: ("p", "P"),
    ecodes.KEY_LEFTBRACE: ("[", "{"),
    ecodes.KEY_RIGHTBRACE: ("]", "}"),
    ecodes.KEY_A: ("a", "A"),
    ecodes.KEY_S: ("s", "S"),
    ecodes.KEY_D: ("d", "D"),
    ecodes.KEY_F: ("f", "F"),
    ecodes.KEY_G: ("g", "G"),
    ecodes.KEY_H: ("h", "H"),
    ecodes.KEY_J: ("j", "J"),
    ecodes.KEY_K: ("k", "K"),
    ecodes.KEY_L: ("l", "L"),
    ecodes.KEY_SEMICOLON: (";", ":"),
    ecodes.KEY_APOSTROPHE: ("'", '"'),
    ecodes.KEY_GRAVE: ("`", "~"),
    ecodes.KEY_BACKSLASH: ("\\", "|"),
    ecodes.KEY_Z: ("z", "Z"),
    ecodes.KEY_X: ("x", "X"),
    ecodes.KEY_C: ("c", "C"),
    ecodes.KEY_V: ("v", "V"),
    ecodes.KEY_B: ("b", "B"),
    ecodes.KEY_N: ("n", "N"),
    ecodes.KEY_M: ("m", "M"),
    ecodes.KEY_COMMA: (",", "<"),
    ecodes.KEY_DOT: (".", ">"),
    ecodes.KEY_SLASH: ("/", "?"),
    ecodes.KEY_SPACE: (" ", " "),
}


def find_scanner() -> InputDevice | None:
    """Find the scanner device by name."""
    for path in list_devices():
        dev = InputDevice(path)
        if SCANNER_DEVICE_NAME in dev.name:
            log.info("Found scanner: %s at %s", dev.name, dev.path)
            return dev
    return None


async def read_scans(callback):
    """Continuously read QR scans and call callback(text) for each.

    Handles device discovery, exclusive grab, and auto-reconnect.
    """
    while True:
        dev = find_scanner()
        if dev is None:
            log.info("Scanner not found, retrying in %ss...", SCANNER_RECONNECT_SECONDS)
            await asyncio.sleep(SCANNER_RECONNECT_SECONDS)
            continue

        try:
            dev.grab()
            log.info("Grabbed scanner exclusively")
        except OSError:
            log.warning("Could not grab scanner, retrying...")
            await asyncio.sleep(SCANNER_RECONNECT_SECONDS)
            continue

        try:
            await _read_loop(dev, callback)
        except OSError:
            log.warning("Scanner disconnected, will reconnect...")
        finally:
            try:
                dev.ungrab()
            except OSError:
                pass
            await asyncio.sleep(SCANNER_RECONNECT_SECONDS)


async def _read_loop(dev: InputDevice, callback):
    """Read key events and assemble scanned text lines."""
    buffer = ""
    shift = False

    async for event in dev.async_read_loop():
        if event.type != ecodes.EV_KEY:
            continue

        key_event = categorize(event)

        # Track shift state
        if key_event.scancode in (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT):
            shift = key_event.keystate in (key_event.key_down, key_event.key_hold)
            continue

        # Only process key-down events
        if key_event.keystate != key_event.key_down:
            continue

        # Enter = end of scan
        if key_event.scancode == ecodes.KEY_ENTER:
            text = buffer.strip()
            buffer = ""
            if text:
                log.info("Scanned: %s", text)
                await callback(text)
            continue

        # Map keycode to character
        mapping = KEYMAP.get(key_event.scancode)
        if mapping:
            char = mapping[1] if shift else mapping[0]
            buffer += char
