"""
ST7735 LCD driver via UCTRONICS RM0004 I²C bridge.

The RM0004 carries an MCU that bridges I²C (address 0x18) to SPI
for the ST7735S 160x80 panel.  Protocol:

    bus.write_byte_data(0x18, 0x00, cmd)          -> ST7735 command byte
    bus.write_i2c_block_data(0x18, 0x01, [bytes]) -> ST7735 data bytes

On Pi 5 / HAOS the I2C bus number differs from Pi 4 (RP1 chip exposes
buses like i2c-13, i2c-14).  _find_i2c_bus() detects the correct one
automatically by probing all /dev/i2c-* devices for address 0x18.
"""

import glob
import time
import logging
import smbus2

log = logging.getLogger(__name__)

# ── Display geometry ────────────────────────────────────────────────────────
WIDTH  = 160
HEIGHT = 80

# ── I²C bridge ─────────────────────────────────────────────────────────────
I2C_ADDR = 0x18


def _find_i2c_bus(addr: int = I2C_ADDR) -> int:
    """
    Probe all /dev/i2c-* buses and return the number of the first one
    that has a device responding at *addr*.  Falls back to 1 if none found.
    """
    for dev in sorted(glob.glob('/dev/i2c-*'),
                      key=lambda d: int(d.split('-')[-1])):
        bus_num = int(dev.split('-')[-1])
        try:
            b = smbus2.SMBus(bus_num)
            # write_quick sends only the address byte — works for write-only
            # devices like the RM0004 bridge that ignore read requests
            b.write_quick(addr)
            b.close()
            log.info("I2C: found 0x%02x on bus %d (%s)", addr, bus_num, dev)
            return bus_num
        except Exception:
            pass
    log.warning("I2C: 0x%02x not found on any bus — defaulting to bus 1", addr)
    return 1


I2C_BUS = _find_i2c_bus()
REG_CMD  = 0x00   # write to this register → ST7735 command
REG_DATA = 0x01   # write to this register → ST7735 data

# ── ST7735 command set ──────────────────────────────────────────────────────
_NOP      = 0x00
_SWRESET  = 0x01
_SLPOUT   = 0x11
_NORON    = 0x13
_INVOFF   = 0x20
_INVON    = 0x21
_DISPOFF  = 0x28
_DISPON   = 0x29
_CASET    = 0x2A
_RASET    = 0x2B
_RAMWR    = 0x2C
_MADCTL   = 0x36
_COLMOD   = 0x3A
_FRMCTR1  = 0xB1
_FRMCTR2  = 0xB2
_FRMCTR3  = 0xB3
_INVCTR   = 0xB4
_PWCTR1   = 0xC0
_PWCTR2   = 0xC1
_PWCTR3   = 0xC2
_PWCTR4   = 0xC3
_PWCTR5   = 0xC4
_VMCTR1   = 0xC5
_GMCTRP1  = 0xE0
_GMCTRN1  = 0xE1

# MADCTL for 160×80 landscape, RGB order.
# If image appears rotated/mirrored, try: 0x00, 0xA0, 0xC0, 0x60
_MADCTL_VAL = 0x70   # MY=0, MX=1, MV=1, ML=1, BGR=0, MH=0

# I²C block-write limit for smbus2 (31 payload bytes + 1 register byte = 32)
_CHUNK = 31


class ST7735:
    """ST7735S driver.  Call :meth:`init` once before any drawing."""

    def __init__(self, bus_num: int = I2C_BUS, addr: int = I2C_ADDR,
                 width: int = WIDTH, height: int = HEIGHT):
        self.bus    = smbus2.SMBus(bus_num)
        self.addr   = addr
        self.width  = width
        self.height = height
        self._on    = True   # backlight state

    # ── Low-level I²C bridge ────────────────────────────────────────────────

    def _cmd(self, cmd: int) -> None:
        """Send one ST7735 command byte via the I²C bridge."""
        self.bus.write_byte_data(self.addr, REG_CMD, cmd & 0xFF)

    def _data(self, data) -> None:
        """Send one or more ST7735 data bytes via the I²C bridge."""
        if isinstance(data, int):
            self.bus.write_byte_data(self.addr, REG_DATA, data & 0xFF)
        else:
            data = list(data)
            for i in range(0, len(data), _CHUNK):
                self.bus.write_i2c_block_data(self.addr, REG_DATA,
                                              data[i:i + _CHUNK])

    # ── Initialisation sequence ─────────────────────────────────────────────

    def init(self) -> None:
        """
        Full ST7735S initialisation.  Must be called once after power-on.
        This is the sequence the C driver omits on Pi 5, causing the display
        to stay stuck on the boot-logo.
        """
        log.info("ST7735: starting init sequence")

        # Software reset — forces the panel out of any previous state
        self._cmd(_SWRESET)
        time.sleep(0.15)

        # Wake from sleep
        self._cmd(_SLPOUT)
        time.sleep(0.25)

        # Frame-rate control (normal / idle / partial)
        self._cmd(_FRMCTR1); self._data([0x01, 0x2C, 0x2D])
        self._cmd(_FRMCTR2); self._data([0x01, 0x2C, 0x2D])
        self._cmd(_FRMCTR3); self._data([0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D])

        # Display-inversion control
        self._cmd(_INVCTR);  self._data([0x07])

        # Power-supply settings
        self._cmd(_PWCTR1);  self._data([0xA2, 0x02, 0x84])
        self._cmd(_PWCTR2);  self._data([0xC5])
        self._cmd(_PWCTR3);  self._data([0x0A, 0x00])
        self._cmd(_PWCTR4);  self._data([0x8A, 0x2A])
        self._cmd(_PWCTR5);  self._data([0x8A, 0xEE])

        # VCOM control
        self._cmd(_VMCTR1);  self._data([0x0E])

        # No inversion
        self._cmd(_INVOFF)

        # Memory access control → landscape 160×80
        self._cmd(_MADCTL);  self._data([_MADCTL_VAL])

        # 16-bit colour (RGB565)
        self._cmd(_COLMOD);  self._data([0x05])

        # Gamma tables (Adafruit-derived, works well with ST7735S)
        self._cmd(_GMCTRP1)
        self._data([0x02, 0x1C, 0x07, 0x12, 0x37, 0x32, 0x29, 0x2D,
                    0x29, 0x25, 0x2B, 0x39, 0x00, 0x01, 0x03, 0x10])
        self._cmd(_GMCTRN1)
        self._data([0x03, 0x1D, 0x07, 0x06, 0x2E, 0x2C, 0x29, 0x2D,
                    0x2E, 0x2E, 0x37, 0x3F, 0x00, 0x00, 0x02, 0x10])

        # Normal display mode on, then display on
        self._cmd(_NORON);  time.sleep(0.01)
        self._cmd(_DISPON); time.sleep(0.10)

        log.info("ST7735: init complete")

    # ── Pixel window ────────────────────────────────────────────────────────

    def _set_window(self, x0: int = 0, y0: int = 0,
                    x1: int = None, y1: int = None) -> None:
        if x1 is None: x1 = self.width  - 1
        if y1 is None: y1 = self.height - 1
        self._cmd(_CASET); self._data([0x00, x0, 0x00, x1])
        self._cmd(_RASET); self._data([0x00, y0, 0x00, y1])
        self._cmd(_RAMWR)

    # ── Public drawing API ──────────────────────────────────────────────────

    def display(self, image) -> None:
        """
        Push a PIL ``Image`` (RGB, 160×80) to the display.

        Converts RGB888 → RGB565 big-endian, then streams all
        25 600 bytes over I²C in 31-byte chunks (~0.6 s at 400 kHz).
        """
        from PIL import Image as _Image
        if image.mode != 'RGB':
            image = image.convert('RGB')
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))

        pixels = image.getdata()
        buf = bytearray(self.width * self.height * 2)
        idx = 0
        for r, g, b in pixels:
            # RGB888 → RGB565 big-endian
            hi = (r & 0xF8) | (g >> 5)
            lo = ((g & 0x1C) << 3) | (b >> 3)
            buf[idx]     = hi
            buf[idx + 1] = lo
            idx += 2

        self._set_window()
        self._data(buf)

    def clear(self, color: tuple = (0, 0, 0)) -> None:
        """Fill the display with a solid colour (default black)."""
        from PIL import Image as _Image
        img = _Image.new('RGB', (self.width, self.height), color)
        self.display(img)

    def set_backlight(self, on: bool) -> None:
        """
        Toggle the display on/off (dim/wake via DISPON/DISPOFF).
        The RM0004 does not expose a separate backlight GPIO.
        """
        self._on = on
        self._cmd(_DISPON if on else _DISPOFF)
        log.debug("Backlight %s", "ON" if on else "OFF")

    def close(self) -> None:
        """Release the I²C bus."""
        try:
            self.bus.close()
        except Exception:
            pass
