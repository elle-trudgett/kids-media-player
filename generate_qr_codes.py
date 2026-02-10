#!/usr/bin/env python3
"""Generate printable QR code PNGs for video files and commands."""

import argparse
import sys
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

from config import COMMAND_PREFIX, COMMANDS, MEDIA_DIR, QR_CODES_DIR, VIDEO_EXTENSIONS


def generate_qr(text: str, label: str, output_path: Path) -> None:
    """Generate a QR code PNG with a label underneath."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(text)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Add label below QR code
    qr_w, qr_h = qr_img.size
    label_height = 60
    padding = 20
    total_h = qr_h + label_height + padding

    canvas = Image.new("RGB", (qr_w, total_h), "white")
    canvas.paste(qr_img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_x = (qr_w - text_w) // 2
    text_y = qr_h + padding // 2
    draw.text((text_x, text_y), label, fill="black", font=font)

    canvas.save(output_path)


def generate_for_media() -> int:
    """Generate QR codes for all video files in the media directory."""
    if not MEDIA_DIR.exists():
        print(f"Media directory not found: {MEDIA_DIR}")
        return 0

    count = 0
    for f in sorted(MEDIA_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
            stem = f.stem
            out = QR_CODES_DIR / f"{stem}.png"
            generate_qr(stem, stem, out)
            print(f"  {out.name}")
            count += 1
    return count


def generate_for_commands() -> int:
    """Generate QR codes for all supported commands."""
    count = 0
    for cmd in sorted(COMMANDS):
        text = f"{COMMAND_PREFIX}{cmd}"
        out = QR_CODES_DIR / f"CMD-{cmd}.png"
        generate_qr(text, cmd, out)
        print(f"  {out.name}")
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate QR codes for kids media player")
    parser.add_argument(
        "--commands-only",
        action="store_true",
        help="Only generate command QR codes (no media scan needed)",
    )
    parser.add_argument(
        "--media-only",
        action="store_true",
        help="Only generate QR codes for media files",
    )
    args = parser.parse_args()

    QR_CODES_DIR.mkdir(parents=True, exist_ok=True)

    total = 0

    if not args.commands_only:
        print("Generating QR codes for media files:")
        total += generate_for_media()

    if not args.media_only:
        print("Generating command QR codes:")
        total += generate_for_commands()

    if total == 0:
        print("No QR codes generated. Add video files to the media/ directory first.")
    else:
        print(f"\nGenerated {total} QR code(s) in {QR_CODES_DIR}/")


if __name__ == "__main__":
    main()
