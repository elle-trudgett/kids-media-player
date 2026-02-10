"""Configuration constants for kids-media-player."""

from pathlib import Path

# Base directory (where this script lives)
BASE_DIR = Path(__file__).resolve().parent

# Media and asset paths
MEDIA_DIR = BASE_DIR / "media"
ASSETS_DIR = BASE_DIR / "assets"
QR_CODES_DIR = BASE_DIR / "qr-codes"
SPLASH_IMAGE = ASSETS_DIR / "splash.png"

# mpv IPC socket
MPV_SOCKET = "/tmp/kids-mpv-socket"

# mpv command to launch
MPV_CMD = [
    "mpv",
    "--idle=yes",
    "--force-window=yes",
    "--fullscreen=yes",
    f"--input-ipc-server={MPV_SOCKET}",
    "--image-display-duration=inf",
    "--no-input-default-bindings",
    "--input-conf=" + str(Path(__file__).resolve().parent / "mpv-input.conf"),
    "--no-osc",
    "--cursor-autohide=always",
    "--hwdec=auto",
    "--no-terminal",
    "--really-quiet",
]

# Supported video extensions (lowercase)
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".webm", ".mov", ".m4v", ".ts", ".flv"}

# QR code command prefix and supported commands
COMMAND_PREFIX = "CMD:"
COMMANDS = {"PAUSE", "STOP", "VOLUP", "VOLDOWN", "MUTE", "FWD", "RWD", "EXIT"}

# Seek step (seconds)
SEEK_STEP = 10

# Scanner settings
SCANNER_DEVICE_NAME = "SCANNER"
SCAN_DEBOUNCE_SECONDS = 2.0
SCANNER_RECONNECT_SECONDS = 3.0

# Idle watcher poll interval
IDLE_POLL_SECONDS = 1.0

# Volume step (percentage)
VOLUME_STEP = 5
