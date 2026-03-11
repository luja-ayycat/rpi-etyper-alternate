A fork of a [T-KONES etyper Landscape branch](https://github.com/T-KONES/rpi-etyper/tree/landscape) designed to work with the Raspberry Pi Zero 2W, which is fork of [etyper](https://github.com/Quackieduckie/etyper).

My brother and I were having trouble getting the T-KONES fork to work so we started expirementing and cleaning up some of the slapdash documentation left in both on the README.md (the main page), and epd42_driver.py

> ***Currently attempting testing on the **Raspberry Pi Zero 2W** running **64-bit Raspberry Pi OS (Debian 12) Armbian Lite (Bookworm)** with a **Waveshare 4.2" V2 e-Paper Module**. Will update if we can get it working properly.***
 
---

# Getting started

### 1. Pray to the Machine God
Considering how much trouble we've had trying to get this working, it can only help.

### 2. Hardware Setup

- **Display**: Waveshare 4.2" V2 display
- **SBC**: Raspberry Pi Zero 2W Rev 1.0
- **A microSD card** and some way to write to it

**Wiring the Waveshare to the Raspberry Pi Zero**

Arranged as it physically appears on the Waveshare Display itself:
|DISPLAY | WIRE COLOR | PIN # | RASPI GPIO ##|
|--------|-----------|---------|-------------|
|BUSY    | Purple    |  PIN 18 | GPIO 24|
|RST     | White     |  PIN 11 | GPIO 17|
|DC      | Green     |  PIN 22 | GPIO 25|
|CS      | Orange    |  PIN 24 | GPIO 8|
|CLK     | Yellow    |  PIN 23 | GPIO 11|
|DIN/MOSI | Blue      |  PIN 19 | GPIO 10|
|GND     | Red       |  PIN 20 | GND|
|VCC     | Gray      |  PIN 17 | PWR |

[Waveshare display manufacturer pinout reference](https://www.waveshare.com/wiki/4.2inch_e-Paper_Module_Manual#Working_With_Raspberry_Pi)
[Rasberry Pi pinout reference](https://pinout.xyz/)

---

# Software Setup

### 1. Getting the OS
Armbian Lite (bookworm) (Debian 12 -Legacy) [Written to microSD via the Raspberry Pi Imager](https://www.raspberrypi.com/software/)

In the setup configuration, before you write, give your Pi a hostname, enable SSH, and enable the WiFi to connect to your local router. Set your username and password too.

Once you insert your micro SD card and power on, you can use [Putty, or another SSH client](https://putty.org) to connect to your Pi using the hostname you chose, and then sign in using whatever credentials you set, if you set any. If all goes right, you should be SSH-ed in, looking at the terminal.

### 2. Enable SPI
To enable hardware SPI via command `sudo raspi-config`

navigate to INTERFACE > SPI then select YES. Then preform a reboot using `sudo reboot`

Check to see is the SPI interface is correctly running `ls /dev/spidev*`

This is return something like spidev0.0 and/or spidev0.1
As this is supposed to run off of 0.0, if you get 0.1 showing up it could be a problem.

### 3. Update packages and install Git
`sudo apt update`
then
`sudo apt install git`
I don't know if you need to install the extra things that Git asks you to install. We chose yes.

### 4. Clone this repo
`git clone --branch landscape --single-branch https://github.com/luja-ayycat/rpi-etyper`

### 5. Install dependencies and service

Use the included installer, which installs all dependencies, disables the conflicting system dnsmasq service, and optionally sets up auto-start on boot:

```bash
cd rpi-etyper
sudo bash install.sh
```

Or install manually:

```bash
apt-get update
apt-get install python3-spidev python3-libgpiod python3-pil python3-evdev \
               python3-dbus python3-gi dnsmasq openssl
systemctl disable --now dnsmasq   # prevent conflict with etyper's own instance
```

> `python3-libgpiod`, `python3-evdev`, `python3-dbus`, and `python3-gi` must be installed via apt (not pip).
> `dnsmasq` is required for Bluetooth file transfer. The system dnsmasq service must be disabled to avoid a port conflict.

### 5. Run the typewriter

```bash
sudo python3 typewriter.py
```

Or to test the display separately:

```bash
python3 examples/hello_world.py
```

## Usage

```python
from epd42_driver import EPD42
from PIL import Image, ImageDraw, ImageFont

with EPD42() as epd:
    # Initialize and clear
    epd.init()
    epd.clear()
    epd.sleep()

    # Create an image
    img = Image.new("1", (epd.width, epd.height), 255)  # white background
    draw = ImageDraw.Draw(img)
    draw.text((50, 100), "Hello!", fill=0)

    # Display it
    epd.init()
    epd.display_image(img)
    epd.sleep()
```
---
# etyper program and features

> **Disclaimer**: This project was mostly generated with AI assistance (Claude / Cursor). Further modified in this fork based on feedback from ChatGPT (probably should have used Claude tho)
> It has been tested on real hardware but may contain bugs or suboptimal patterns.
> Contributions and corrections are welcome.
> **Known issues:**  The keyboard layout picker screen is a little wonky in landscape. The options extend past the bottom margin, causing the Colemak layout option to appear offscreen (it's still there and has NOT been removed! Just scroll down until the black highlight disappears).
## Typewriter Mode

etyper includes a distraction-free typewriter application inspired by [ZeroWriter](https://github.com/zerowriter/zerowriter1).

**Features:**
- Portrait display (rotated 90 CCW, 300x400 effective resolution)
- Auto-opens last document on startup
- Autosave every 10 seconds
- USB keyboard input (any standard USB keyboard)
- Switchable keyboard layout: US QWERTY, UK QWERTY, DE QWERTZ, FR AZERTY, ES QWERTY, IT QWERTY, SE QWERTY, NO/DK QWERTY, Colemak, US DVORAK (Ctrl+K)
- Full text editing with arrow key cursor movement
- Word wrap, auto-scrolling to follow cursor
- Partial refresh for fast typing response (~0.5s per update)
- Time-based full refresh every 5 minutes to clean e-paper ghosting
- Auto-start on boot via systemd service
- Survives power outages (autosave + auto-start + e-paper retains image)

### Keyboard Commands

**Typing:**
| Key | Action |
|-----|--------|
| A-Z, 0-9, symbols | Insert character at cursor position |
| Space | Insert space |
| Enter | Insert new line |
| Tab | Insert 4 spaces |
| Backspace | Delete character before cursor |
| Delete | Delete character after cursor |

**Cursor movement:**
| Key | Action |
|-----|--------|
| Left arrow | Move cursor one character left |
| Right arrow | Move cursor one character right |
| Up arrow | Move cursor up one visual line |
| Down arrow | Move cursor down one visual line |
| Home | Jump to start of current line |
| End | Jump to end of current line |

**Shortcuts:**
| Shortcut | Action |
|----------|--------|
| Ctrl+S | Save document |
| Ctrl+N | Save current and create new document |
| Ctrl+Left | Switch to previous document |
| Ctrl+Right | Switch to next document |
| Ctrl+F | Toggle file server via Bluetooth (download docs in browser) |
| Ctrl+K | Choose keyboard layout (Up/Down to browse, Enter to select, Esc to cancel) |
| Ctrl+R | Force full display refresh (cleans ghosting) |
| Ctrl+Q | Sleep / wake toggle (saves on sleep) |

### Status Bar

The bottom of the screen shows: `*doc_20260115_143022.txt L12:5 482c`
- `*` = unsaved changes (disappears after save/autosave)
- `L12:5` = cursor at line 12, column 5
- `482c` = total character count

---

### Running

**Run manually:**
```bash
sudo python3 typewriter.py
```

**Run as boot service (auto-starts on power on):**
```bash
sudo bash install.sh
# Or manually (replace /path/to/etyper with your actual install path):
sed "s|__INSTALL_DIR__|/path/to/etyper|g" etyper.service | sudo tee /etc/systemd/system/etyper.service
sudo systemctl daemon-reload
sudo systemctl enable --now etyper
```

**Service management:**
```bash
sudo systemctl status etyper    # Check status
sudo systemctl stop etyper      # Stop
sudo systemctl start etyper     # Start
sudo systemctl restart etyper   # Restart after code changes
journalctl -u etyper -f         # View live logs
```

### Documents

- Saved to `~/etyper_docs/` as plain `.txt` files
- Filenames are timestamped: `doc_20260115_143022.txt`
- Last opened document is tracked in `~/etyper_docs/.last_doc`
- On startup, the last document is automatically reopened with cursor at the end

### File Transfer (Ctrl+F)

Download your documents wirelessly via Bluetooth PAN (Personal Area Network). No WiFi required — the etyper creates its own network over Bluetooth.

**How it works:**
1. Press **Ctrl+F** — Bluetooth powers on, the file server starts, and instructions appear on screen
2. On your computer, open **Bluetooth settings** and pair with **"etyper"** (auto-accepts, no PIN needed)
3. Once paired, open a browser and go to **`https://10.44.0.1`** (accept the certificate warning)
4. Download individual documents or all at once as a `.zip` file
5. Press **Ctrl+F** again to stop — devices are disconnected and Bluetooth powers off

**Notes:**
- Bluetooth is **off by default** and only activates during file transfer
- Auto-shuts down after **5 minutes** if you forget to stop it
- **Pairings are preserved** — once you pair a device, it can reconnect next time without re-pairing
- SSL certificate persists across reboots (stored in `~/etyper_docs/.ssl/`)
- Survives crashes: stale bridges and DHCP servers are cleaned up automatically on startup
- Works best with desktop/laptop browsers — phone Bluetooth PAN support varies by device
- If your browser forces HTTPS errors, try `http://10.44.0.1:8080` as a fallback
- Requires `python3-dbus`, `python3-gi`, and `dnsmasq` on the Pi


### API Reference

| Method | Description |
|--------|-------------|
| `EPD42(pins, spi_bus, spi_dev, spi_speed, spi_mode, gpiochip)` | Constructor with optional config |
| `epd.init()` | Initialize display for full refresh |
| `epd.init_partial()` | Switch to partial refresh mode (call after `init` + `display`) |
| `epd.display(buffer)` | Write raw buffer and full refresh (~4s) |
| `epd.display_partial(buffer)` | Write raw buffer and partial refresh (~0.5s) |
| `epd.display_image(image)` | Display a PIL Image with full refresh |
| `epd.display_image_partial(image)` | Display a PIL Image with partial refresh |
| `epd.full_refresh(buffer)` | Force a full refresh to clean ghosting |
| `epd.clear(color=0xFF)` | Clear to white (0xFF) or black (0x00) |
| `epd.sleep()` | Enter deep sleep (requires `init()` to wake) |
| `epd.reset()` | Hardware reset |
| `epd.close()` | Release GPIO and SPI resources |
| `EPD42.getbuffer(image)` | Static: convert PIL Image to raw buffer |


## Technical Details

- **SPI**: Hardware SPI0 at 4MHz, Mode 0.
- **Full refresh**: ~4 seconds, no ghosting. Used on startup and every 5 minutes.
- **Partial refresh**: ~0.5 seconds, slight ghosting. Used for typing updates.
- **Display buffer**: 15,000 bytes (400/8 * 300). 1 bit per pixel, MSB first. 1=white, 0=black.
- **Deep sleep**: ~1uA current draw. Requires hardware reset to wake.
- **Typewriter font**: [Atkinson Hyperlegible Mono](https://github.com/googlefonts/atkinson-hyperlegible-next-mono) Medium 16px, 28 chars x 15 lines in portrait mode. Line height follows WCAG 1.5x recommendation. Designed by the Braille Institute for maximum legibility on low-resolution displays. Falls back to DejaVu Sans Mono if not found. Licensed under SIL Open Font License 1.1.
- **File transfer**: Bluetooth PAN (NAP) with auto-accept D-Bus agent, bridge networking, dnsmasq DHCP, and HTTPS (self-signed cert) + HTTP fallback. Bluetooth is powered off when not in use. Pairings are preserved across sessions; stale state is cleaned up on startup for crash resilience.

## Project Structure

```
etyper/
  epd42_driver.py          # E-paper display driver (full + partial refresh)
  typewriter.py            # Typewriter application
  install.sh               # Installer (dependencies + systemd service)
  etyper.service           # systemd unit file
  requirements.txt         # Python dependencies
  README.md                # This file
  fonts/
    AtkinsonHyperlegibleMono-Medium.ttf    # Primary display font
    AtkinsonHyperlegibleMono-SemiBold.ttf  # Heavier variant
    AtkinsonHyperlegibleMono-Regular.ttf   # Lighter variant
    AtkinsonHyperlegibleMono-Bold.ttf      # Bold variant
    OFL.txt                                # SIL Open Font License
  examples/
    hello_world.py         # Basic "Hello World" demo
    test_patterns.py       # Diagnostic test patterns
```

## Credits

- [WeAct Studio](https://github.com/WeActStudio/WeActStudio.EpaperModule) - Display manufacturer & reference C driver
- [Waveshare](https://github.com/waveshare/e-Paper) - Compatible Python driver reference
- [Atkinson Hyperlegible Mono](https://github.com/googlefonts/atkinson-hyperlegible-next-mono) - Display font by the Braille Institute (SIL OFL 1.1)
