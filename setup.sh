#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="kids-media-player"
SERVICE_SRC="$SCRIPT_DIR/systemd/${SERVICE_NAME}.service"
SERVICE_DEST="$HOME/.config/systemd/user/${SERVICE_NAME}.service"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[x]${NC} $*"; }

install() {
    info "Installing Kids QR-Code Media Player"
    echo

    # --- apt packages ---
    info "Installing system packages..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq mpv

    # --- pip packages ---
    info "Installing Python packages..."
    pip install --break-system-packages -q evdev "qrcode[pil]"

    # --- directories ---
    info "Creating directories..."
    mkdir -p "$SCRIPT_DIR/media"
    mkdir -p "$SCRIPT_DIR/qr-codes"
    mkdir -p "$SCRIPT_DIR/assets"

    # --- splash screen ---
    if [ ! -f "$SCRIPT_DIR/assets/splash.png" ]; then
        info "Generating splash screen..."
        SCRIPT_DIR="$SCRIPT_DIR" python3 -c "
import os, math, random
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
img = Image.new('RGB', (W, H), (25, 25, 50))
draw = ImageDraw.Draw(img)

# Gradient background: deep purple to dark blue
for y in range(H):
    t = y / H
    r = int(25 + 15 * t)
    g = int(20 + 10 * (1 - t))
    b = int(60 + 40 * t)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# Scatter soft circles as bokeh/stars
random.seed(42)
for _ in range(60):
    x = random.randint(0, W)
    y = random.randint(0, H)
    radius = random.randint(3, 25)
    alpha = random.randint(15, 50)
    color = random.choice([
        (255, 220, 100, alpha),
        (100, 200, 255, alpha),
        (255, 150, 200, alpha),
        (150, 255, 180, alpha),
    ])
    # Draw filled circle with low opacity via overlay
    overlay = Image.new('RGBA', (radius * 2, radius * 2), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.ellipse([0, 0, radius * 2, radius * 2], fill=color)
    img.paste(
        Image.alpha_composite(
            img.crop((x - radius, y - radius, x + radius, y + radius)).convert('RGBA'),
            overlay
        ).convert('RGB'),
        (x - radius, y - radius)
    )

# Decorative top and bottom bars
draw = ImageDraw.Draw(img)
for i in range(4):
    alpha_frac = (4 - i) / 4
    c = int(255 * alpha_frac * 0.15)
    draw.rectangle([0, i * 2, W, i * 2 + 1], fill=(c, c, int(c * 1.5)))
    draw.rectangle([0, H - i * 2 - 1, W, H - i * 2], fill=(c, c, int(c * 1.5)))

try:
    font_big = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 80)
    font_sub = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 36)
except OSError:
    font_big = ImageFont.load_default()
    font_sub = font_big

# Main title
title = 'Scan a code to watch!'
bbox = draw.textbbox((0, 0), title, font=font_big)
tx = (W - (bbox[2] - bbox[0])) // 2
ty = 400
# Text shadow
draw.text((tx + 3, ty + 3), title, fill=(0, 0, 0), font=font_big)
draw.text((tx, ty), title, fill=(255, 255, 255), font=font_big)

# Subtitle
sub = 'Find a show in your book and scan the QR code'
bbox2 = draw.textbbox((0, 0), sub, font=font_sub)
sx = (W - (bbox2[2] - bbox2[0])) // 2
sy = ty + 110
draw.text((sx + 2, sy + 2), sub, fill=(0, 0, 0), font=font_sub)
draw.text((sx, sy), sub, fill=(180, 190, 220), font=font_sub)

out = os.path.join(os.environ['SCRIPT_DIR'], 'assets', 'splash.png')
img.save(out)
print(f'  Saved {out}')
"
    else
        info "Splash screen already exists, skipping"
    fi

    # --- input group ---
    if ! groups "$USER" | grep -q '\binput\b'; then
        info "Adding $USER to input group (for scanner access)..."
        sudo usermod -aG input "$USER"
        warn "You may need to log out and back in for group changes to take effect"
    else
        info "User already in input group"
    fi

    # --- systemd service ---
    info "Installing systemd user service..."
    mkdir -p "$(dirname "$SERVICE_DEST")"
    cp "$SERVICE_SRC" "$SERVICE_DEST"
    systemctl --user daemon-reload
    systemctl --user enable "$SERVICE_NAME"

    echo
    info "Installation complete!"
    echo
    echo "  Next steps:"
    echo "    1. Copy video files to: $SCRIPT_DIR/media/"
    echo "    2. Generate QR codes:   python3 $SCRIPT_DIR/generate_qr_codes.py"
    echo "    3. Start the player:    ./start.sh"
    echo "    4. Or reboot and it starts automatically"
    echo
    echo "  To stop:       ./stop.sh"
    echo "  To check status: systemctl --user status $SERVICE_NAME"
    echo "  To view logs:    journalctl --user -u $SERVICE_NAME -f"
}

uninstall() {
    info "Uninstalling Kids QR-Code Media Player"
    echo

    info "Stopping service..."
    systemctl --user stop "$SERVICE_NAME" 2>/dev/null || true

    info "Disabling service..."
    systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true

    if [ -f "$SERVICE_DEST" ]; then
        info "Removing service file..."
        rm "$SERVICE_DEST"
        systemctl --user daemon-reload
    fi

    echo
    info "Service removed. Your media files and QR codes are untouched."
    echo "  To fully remove, delete: $SCRIPT_DIR"
}

case "${1:-}" in
    install)
        install
        ;;
    uninstall)
        uninstall
        ;;
    *)
        echo "Usage: $0 {install|uninstall}"
        exit 1
        ;;
esac
