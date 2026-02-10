"""mpv JSON IPC client: send commands over Unix socket."""

import json
import socket
import logging

from config import MPV_SOCKET

log = logging.getLogger(__name__)


def _send(command: list) -> dict | None:
    """Open a fresh connection, send one command, return the response."""
    payload = json.dumps({"command": command}) + "\n"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(2.0)
            sock.connect(MPV_SOCKET)
            sock.sendall(payload.encode())
            data = b""
            while b"\n" not in data:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            if data:
                return json.loads(data.decode().split("\n")[0])
    except (ConnectionRefusedError, FileNotFoundError):
        log.warning("mpv socket not available")
    except Exception:
        log.exception("mpv IPC error")
    return None


def load_file(path: str) -> bool:
    """Load a file (video or image) replacing current playback."""
    resp = _send(["loadfile", path])
    return resp is not None and resp.get("error") == "success"


def stop() -> bool:
    """Stop playback and return to idle."""
    resp = _send(["stop"])
    return resp is not None and resp.get("error") == "success"


def pause_toggle() -> bool:
    """Toggle pause/unpause."""
    resp = _send(["cycle", "pause"])
    return resp is not None and resp.get("error") == "success"


def volume_up(step: int = 5) -> bool:
    """Increase volume by step percent."""
    resp = _send(["add", "volume", str(step)])
    return resp is not None and resp.get("error") == "success"


def volume_down(step: int = 5) -> bool:
    """Decrease volume by step percent."""
    resp = _send(["add", "volume", str(-step)])
    return resp is not None and resp.get("error") == "success"


def mute_toggle() -> bool:
    """Toggle mute."""
    resp = _send(["cycle", "mute"])
    return resp is not None and resp.get("error") == "success"


def seek(seconds: int) -> bool:
    """Seek relative by given seconds (negative = backward)."""
    resp = _send(["seek", str(seconds), "relative"])
    return resp is not None and resp.get("error") == "success"


def get_property(name: str):
    """Get an mpv property value, or None on error."""
    resp = _send(["get_property", name])
    if resp and resp.get("error") == "success":
        return resp.get("data")
    return None


def is_idle() -> bool:
    """Check if mpv is in idle state (no file playing)."""
    val = get_property("idle-active")
    return val is True
