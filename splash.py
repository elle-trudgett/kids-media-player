"""Generate the splash screen image with a live clock."""

import logging
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from config import SPLASH_IMAGE, ASSETS_DIR

log = logging.getLogger(__name__)

W, H = 1920, 1080


def _load_fonts():
    """Load fonts, falling back to defaults."""
    try:
        return {
            "big": ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80),
            "sub": ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36),
            "clock": ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 200),
        }
    except OSError:
        default = ImageFont.load_default()
        return {"big": default, "sub": default, "clock": default}


def _center_x(draw, text, font):
    """Get x coordinate to center text horizontally."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return (W - (bbox[2] - bbox[0])) // 2


def generate():
    """Generate splash.png with current time. Returns the path."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    fonts = _load_fonts()

    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # Gradient background: deep purple to dark blue
    for y in range(H):
        t = y / H
        r = int(10 + 30 * t)
        g = int(8 + 22 * t)
        b = int(25 + 75 * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Random offset to prevent burn-in (shifts each minute)
    ox = random.randint(-150, 150)
    oy = random.randint(-100, 100)

    # Clock
    now = datetime.now()
    time_str = now.strftime("%-I:%M %p").replace("AM", "am").replace("PM", "pm")
    tx = _center_x(draw, time_str, fonts["clock"]) + ox
    ty = 220 + oy
    draw.text((tx + 4, ty + 4), time_str, fill=(0, 0, 0), font=fonts["clock"])
    draw.text((tx, ty), time_str, fill=(140, 140, 170), font=fonts["clock"])

    # Main title
    title = "Scan a code to watch!"
    ttx = _center_x(draw, title, fonts["big"]) + ox
    tty = 500 + oy
    draw.text((ttx + 3, tty + 3), title, fill=(0, 0, 0), font=fonts["big"])
    draw.text((ttx, tty), title, fill=(255, 255, 255), font=fonts["big"])

    # Subtitle
    sub = "Find a show in your book and scan the QR code"
    sx = _center_x(draw, sub, fonts["sub"]) + ox
    sy = tty + 110
    draw.text((sx + 2, sy + 2), sub, fill=(0, 0, 0), font=fonts["sub"])
    draw.text((sx, sy), sub, fill=(180, 190, 220), font=fonts["sub"])

    img.save(SPLASH_IMAGE)
    return str(SPLASH_IMAGE)
