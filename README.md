# Kids QR-Code Media Player

A dedicated Raspberry Pi media player for kids. They pick a show from a book of QR codes, scan it with a USB barcode scanner, and the video plays fullscreen on the TV. No YouTube, no ads, no autoplay rabbit holes - just curated local video files.

## How it works

1. A splash screen with a clock is shown on the TV when nothing is playing
2. The kid finds a show in their QR code book and scans it with the USB scanner
3. The matching video file plays fullscreen
4. When the video ends, the splash screen returns
5. Special command QR codes can pause, stop, adjust volume, or seek

## What you need

- **Raspberry Pi 5** (or 4) with Raspberry Pi OS (Desktop version)
- **HDMI cable** connecting the Pi to your TV
- **USB barcode/QR code scanner** (the kind that acts as a keyboard)
- **Video files** you want the kids to watch
- **Printer** to print the QR codes

## Setup from scratch (new Raspberry Pi)

### 1. Set up your Raspberry Pi

If your Pi is brand new, use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on another computer to flash **Raspberry Pi OS (Desktop)** to your SD card. Boot the Pi, connect it to Wi-Fi, and complete the first-time setup wizard.

### 2. Open a terminal

Click the terminal icon in the top menu bar, or press `Ctrl+Alt+T`.

### 3. Clone this project

```bash
sudo apt install -y git
git clone https://github.com/elle-trudgett/kids-media-player.git ~/code/kids-media-player
cd ~/code/kids-media-player
```

### 4. Run the installer

```bash
./setup.sh install
```

This will:
- Install `mpv` (the video player)
- Install Python dependencies (`evdev`, `qrcode`)
- Generate the splash screen image
- Add your user to the `input` group (for scanner access)
- Install and enable the systemd service for auto-start

**If it says you were added to the `input` group**, log out and back in (or reboot) before continuing.

### 5. Add your video files

Copy video files into the `media/` folder. You can use a USB drive, SCP, or any method you like:

```bash
# From a USB drive (adjust the path to your drive)
cp /media/yourusername/USBDRIVE/*.mp4 ~/code/kids-media-player/media/

# Or from another computer via SCP
scp videos/*.mp4 yourusername@raspberrypi.local:~/code/kids-media-player/media/
```

Supported formats: `.mp4`, `.mkv`, `.avi`, `.webm`, `.mov`, `.m4v`, `.ts`, `.flv`

### 6. Generate QR codes

```bash
cd ~/code/kids-media-player
python3 generate_qr_codes.py
```

This creates a PNG image for each video file in `qr-codes/`. Each QR code contains the filename stem (e.g. `bluey-s1e1`). It also generates command QR codes (pause, stop, etc.).

Print the QR codes and put them in a book or folder for the kids.

### 7. Start the player

```bash
./start.sh
```

Or just **reboot** - the player starts automatically on login.

### 8. Plug in the USB scanner

Plug the USB barcode scanner into the Pi. The player will detect it automatically.

## QR code format

### Video codes

The QR code text is just the video filename without the extension:

| Video file | QR code text |
|---|---|
| `media/bluey-s1e1.mp4` | `bluey-s1e1` |
| `media/peppa-pig-muddy-puddles.mkv` | `peppa-pig-muddy-puddles` |

Matching is case-insensitive.

### Command codes

Command QR codes are prefixed with `CMD:`:

| QR code text | Action |
|---|---|
| `CMD:PAUSE` | Pause / unpause |
| `CMD:STOP` | Stop and return to splash screen |
| `CMD:VOLUP` | Volume up |
| `CMD:VOLDOWN` | Volume down |
| `CMD:MUTE` | Mute / unmute |
| `CMD:FWD` | Skip forward 10 seconds |
| `CMD:RWD` | Rewind 10 seconds |
| `CMD:EXIT` | Quit the player |

Generate command QR codes with:

```bash
python3 generate_qr_codes.py --commands-only
```

## Testing without a scanner

Run the player in keyboard mode to type QR code text manually:

```bash
python3 player.py --keyboard
```

Then type video names or commands like `CMD:PAUSE` and press Enter.

## Managing the service

```bash
# Start the player
./start.sh

# Stop the player
./stop.sh

# Check status
systemctl --user status kids-media-player

# View live logs
journalctl --user -u kids-media-player -f

# Disable auto-start
systemctl --user disable kids-media-player

# Re-enable auto-start
systemctl --user enable kids-media-player
```

## Uninstalling

```bash
./setup.sh uninstall
```

This stops and removes the systemd service. Your video files and QR codes are left untouched.

## Configuring

Edit `config.py` to change:

- `SCANNER_DEVICE_NAME` - set this to match your USB scanner (run `python3 -c "from evdev import list_devices, InputDevice; [print(InputDevice(d).name) for d in list_devices()]"` to list devices)
- `VIDEO_EXTENSIONS` - add or remove supported video formats
- `VOLUME_STEP` - volume change per step (default: 5%)
- `SEEK_STEP` - seek time in seconds (default: 10)
- `SCAN_DEBOUNCE_SECONDS` - prevent duplicate scans (default: 2s)

## Troubleshooting

**Player doesn't start / "mpv socket did not appear"**
- Make sure `mpv` is installed: `sudo apt install mpv`
- Check logs: `journalctl --user -u kids-media-player -f`

**Scanner not detected**
- Check your scanner name: `python3 -c "from evdev import list_devices, InputDevice; [print(InputDevice(d).name) for d in list_devices()]"`
- Update `SCANNER_DEVICE_NAME` in `config.py` to match
- Make sure your user is in the `input` group: `groups` (log out/in after adding)

**Video doesn't play when scanned**
- Check the QR code text matches the filename stem exactly (case-insensitive)
- Make sure the video file is in the `media/` directory
- Check logs for "No video found for: ..." messages

**Getting back to the desktop**
- Press Q or ESC on a keyboard plugged into the Pi
- Or scan the `CMD:EXIT` QR code
- Or SSH in: `ssh yourusername@raspberrypi.local` then `./code/kids-media-player/stop.sh`
- The desktop is always running underneath - mpv is just fullscreen on top
- To restart: `./start.sh`
