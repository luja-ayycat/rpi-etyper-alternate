"""
epd42_driver.py - Waveshare 4.2" V2 e-Paper Module Display Driver
SSD1683 controller, 400x300 pixels, Black/White

Target: Raspi 0 2w Rev 1.0 running Armbian (bookworm lite) (debian linux Ver 12)
Uses: spidev (hardware SPI1) + gpiod (libgpiod) for GPIO control

Pin mapping (Waveshare 4.2" V2 e-Paper Module Raspberry Pi header pinout):
  MOSI  -> Pin 19 (GPIO 10, SPI0_MOSI)
  CLK   -> Pin 23 (GPIO 11, SPI0_CLK)
  CS    -> Pin 24 (GPIO 8)
  DC    -> Pin 22 (GPIO 25)
  RST   -> Pin 11 (GPIO 17)
  BUSY  -> Pin 18 (GPIO 24)

According to the 'jippity' the pin out should be this
Arranged as it physically appears on the Waveshare Display itself:
DISPLAY  WIRE COLOR  PIN #    RASPI GPIO ##
BUSY     Purple      PIN 18 | GPIO  24
RST      White       PIN 11 | GPIO 17
DC       Green       PIN 22 | GPIO 25
CS       Orange      PIN 24 | GPIO 8
CLK      Yellow      PIN 23 | GPIO 11
DIN/MOSI Blue        PIN 19 | GPIO 10
GND      Red         PIN 20 | GND
VCC      Gray        PIN 17 | PWR 

Note: Hardware SPI1 CS1 (Pin 26 / PH9) is NOT used.
      CS is controlled manually via GPIO for proper DC/CS timing.
"""

import spidev
import gpiod
import time
from PIL import Image
import subprocess

def _force_release_gpio_lines(pins, chip="gpiochip0"):
    """Force-release stale GPIO claims left by crashed processes."""
    for name, pin in pins.items():
        subprocess.run(
            ["sudo", "gpioset", "--mode=time", "--sec=0", chip, f"{pin}=0"],
            capture_output=True
        )
# Display dimensions
EPD_WIDTH = 400
EPD_HEIGHT = 300

# Default GPIO line numbers (gpiochip0) for Raspberry Pi Zero 2W
DEFAULT_PINS = {
    "dc": 25,    # Pin 22 
    #"cs": 8,    # Pin 24
    "rst": 17,   # Pin 11
    "busy": 24,  # Pin 18
}

# Default SPI settings
DEFAULT_SPI_BUS = 0
DEFAULT_SPI_DEV = 0
DEFAULT_SPI_SPEED = 4_000_000  # 4 MHz
DEFAULT_SPI_MODE = 0b00        # SPI Mode 0


class EPD42:
    """Waveshare 4.2" V2 e-Paper Module" (400x300).

    Supports full refresh, fast refresh, and partial refresh modes.
    """

    def __init__(self, pins=None, spi_bus=DEFAULT_SPI_BUS, spi_dev=DEFAULT_SPI_DEV,
                 spi_speed=DEFAULT_SPI_SPEED, spi_mode=DEFAULT_SPI_MODE,
                 gpiochip="gpiochip0"):
        """
        Initialize the e-paper driver.

        Args:
            pins: dict with keys 'dc', 'cs', 'rst', 'busy' mapping to GPIO line numbers.
                  Defaults to Waveshare 4.2" V2 e-Paper Module pinout.
            spi_bus: SPI bus number (default 0)
            spi_dev: SPI device number (default 0)
            spi_speed: SPI clock speed in Hz (default 4MHz)
            spi_mode: SPI mode (default 0)
            gpiochip: GPIO chip name (default "gpiochip1")
        """
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT
        self.pins = pins or DEFAULT_PINS.copy()
        self._partial_count = 0
        self._last_full_refresh = time.time()
        self._full_refresh_interval = 300  # seconds (5 minutes)

        # SPI setup
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_dev)
        self.spi.max_speed_hz = spi_speed
        self.spi.mode = spi_mode

        # GPIO setup
        self.chip = gpiod.Chip(gpiochip)

        self.dc = self._request_line(self.pins["dc"], gpiod.LINE_REQ_DIR_OUT, default_val=1)
        self.rst = self._request_line(self.pins["rst"], gpiod.LINE_REQ_DIR_OUT, default_val=1)
        self.busy = self._request_line(self.pins["busy"], gpiod.LINE_REQ_DIR_IN)

    def _request_line(self, pin_num, direction, default_val=0):
        """
        Request a GPIO line, releasing and re-requesting if already held.
        This handles the [Errno 16] Device or resource busy error caused by
        a previous run crashing without releasing its GPIO lines.
        """
        line = self.chip.get_line(pin_num)
        kwargs = {"consumer": "epd", "type": direction}
        if direction == gpiod.LINE_REQ_DIR_OUT:
            kwargs["default_vals"] = [default_val]
        else:
            kwargs["flags"] = gpiod.LINE_REQ_FLAG_BIAS_DISABLE

        try:
            line.request(**kwargs)
        except OSError as e:
            if e.errno == 16:  # EBUSY — line held by a dead/crashed consumer
                line.release()
                line = self.chip.get_line(pin_num)
                line.request(**kwargs)
            else:
                raise
        return line

    def close(self):
        """Release all GPIO lines and close SPI."""
        self.dc.release()
        #self.cs.release() #Removing references to CS
        self.rst.release()
        self.busy.release()
        self.spi.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # --- Low-level SPI/GPIO ---

    def _wait_busy(self, timeout=30):
        """Wait for BUSY pin to go LOW (idle). Returns True if cleared."""
        start = time.time()
        while self.busy.get_value() == 1:
            if time.time() - start > timeout:
                return False
            time.sleep(0.01)
        return True

    def _send_command(self, cmd):
        """Send a command byte (DC=LOW)."""
        self.dc.set_value(0)
        #self.cs.set_value(0) #Removing references to CS
        self.spi.writebytes([cmd])
        #self.cs.set_value(1) #Removing references to CS
        self.dc.set_value(1)

    def _send_data(self, val):
        """Send a single data byte (DC=HIGH)."""
        self.dc.set_value(1)
        #self.cs.set_value(0) #Removing references to CS
        self.spi.writebytes([val])
        #self.cs.set_value(1) #Removing references to CS

    def _send_data_bulk(self, data):
        """Send bulk data (DC=HIGH, CS held LOW for entire transfer)."""
        self.dc.set_value(1)
        #self.cs.set_value(0) #Removing references to CS
        chunk_size = 4096
        for i in range(0, len(data), chunk_size):
            self.spi.writebytes(data[i:i + chunk_size])
        #self.cs.set_value(1) #Removing references to CS

    def _set_window(self):
        """Set the RAM window to full screen."""
        self._send_command(0x44)  # RAM X address range
        self._send_data(0x00)
        self._send_data(0x31)

        self._send_command(0x45)  # RAM Y address range
        self._send_data(0x00)
        self._send_data(0x00)
        self._send_data(0x2B)
        self._send_data(0x01)

    def _set_cursor(self):
        """Set the RAM cursor to (0, 0)."""
        self._send_command(0x4E)
        self._send_data(0x00)
        self._send_command(0x4F)
        self._send_data(0x00)
        self._send_data(0x00)

    # --- Display operations ---

    def reset(self):
        """Hardware reset the display."""
        self.rst.set_value(0)
        time.sleep(0.05)
        self.rst.set_value(1)
        time.sleep(0.05)
        self._wait_busy()

    def init(self):
        """Initialize the display for a full refresh cycle."""
        self.reset()

        self._send_command(0x12)  # SW Reset
        time.sleep(0.1)
        self._wait_busy()

        self._send_command(0x21)  # Display Update Control
        self._send_data(0x40)
        self._send_data(0x00)

        self._send_command(0x3C)  # Border Waveform
        self._send_data(0x05)

        self._send_command(0x11)  # Data Entry Mode: X-mode
        self._send_data(0x03)

        self._set_window()
        self._set_cursor()
        self._wait_busy()

    def init_partial(self):
        """Initialize the display for partial refresh mode.

        Call init() and display() first to set both RAM buffers,
        then call init_partial() to switch to partial mode.
        """
        self.init()

        self._send_command(0x3C)  # Border Waveform
        self._send_data(0x80)

        self._send_command(0x21)  # Display Update Control
        self._send_data(0x00)    # RED normal
        self._send_data(0x00)    # single chip application

        self._partial_count = 0
        self._last_full_refresh = time.time()

    def display(self, buffer):
        """
        Write image buffer to display and perform full refresh.

        Args:
            buffer: list/bytes of length (width/8 * height) = 15000.
                    Each bit: 1=white, 0=black. MSB first.
        """
        self._send_command(0x24)  # Write to NEW RAM
        self._send_data_bulk(buffer)

        self._send_command(0x26)  # Write to OLD RAM
        self._send_data_bulk(buffer)

        self._send_command(0x22)  # Display Update Control
        self._send_data(0xF7)
        self._send_command(0x20)  # Activate Display Update Sequence
        self._wait_busy()
        self._last_full_refresh = time.time()
        self._partial_count = 0

    def display_partial(self, buffer):
        """
        Write image buffer and perform partial refresh (faster, slight ghosting).

        Must call init_partial() first. A full refresh is triggered automatically
        every 5 minutes to clean ghosting. Can also be forced with full_refresh().

        Args:
            buffer: list/bytes of length (width/8 * height) = 15000.
        """
        self._partial_count += 1

        # Time-based full refresh to clean ghosting (every 5 min)
        if time.time() - self._last_full_refresh >= self._full_refresh_interval:
            self.init()
            self.display(buffer)
            self.init_partial()
            return

        self._send_command(0x3C)  # Border Waveform
        self._send_data(0x80)

        self._send_command(0x21)  # Display Update Control
        self._send_data(0x00)
        self._send_data(0x00)

        self._set_window()
        self._set_cursor()

        self._send_command(0x24)  # Write to NEW RAM only
        self._send_data_bulk(buffer)

        self._send_command(0x22)  # Display Update Control: partial
        self._send_data(0xFF)
        self._send_command(0x20)  # Activate Display Update Sequence
        self._wait_busy()

        # Sync OLD RAM for next partial
        self._set_cursor()
        self._send_command(0x26)
        self._send_data_bulk(buffer)

    def full_refresh(self, buffer):
        """Force a full refresh to clean ghosting. Use when display looks messy."""
        self.init()
        self.display(buffer)
        self.init_partial()

    def clear(self, color=0xFF):
        """
        Clear the display to a solid color.

        Args:
            color: 0xFF for white (default), 0x00 for black.
        """
        buf = [color] * (self.width // 8 * self.height)
        self.display(buf)

    def sleep(self):
        """Put the display into deep sleep mode. Requires reset to wake."""
        self._send_command(0x10)  # Deep Sleep Mode
        self._send_data(0x01)

    def display_image(self, image):
        """
        Display a PIL Image on the e-paper (full refresh).

        Args:
            image: PIL Image object. Will be converted to 1-bit, resized if needed.
        """
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))
        image = image.convert("1")
        buffer = list(image.tobytes())
        self.display(buffer)

    def display_image_partial(self, image):
        """
        Display a PIL Image using partial refresh (faster).

        Args:
            image: PIL Image object (400x300 or will be resized).
        """
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))
        image = image.convert("1")
        buffer = list(image.tobytes())
        self.display_partial(buffer)

    @staticmethod
    def getbuffer(image):
        """
        Convert a PIL Image to display buffer (Waveshare-compatible).

        Args:
            image: PIL Image (mode "1", size 400x300).

        Returns:
            list of bytes for display().
        """
        return list(image.convert("1").tobytes())
