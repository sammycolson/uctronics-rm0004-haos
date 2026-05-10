#!/usr/bin/env python3
"""
UCTRONICS RM0004 Pi Rack Pro — Home Assistant Add-on
Main display loop.

Pages rotate every PAGE_DURATION seconds:
  0 → IP address   (interface end0)
  1 → CPU usage %
  2 → RAM usage %  + used/total GB
  3 → Disk usage % + used/total GB
  4 → CPU temperature

Power button (BCM GPIO 4 / gpiochip4):
  short press → toggle display on/off
  long  press → ha host shutdown via Supervisor API
"""

import os
import signal
import sys
import time
import logging

from PIL import Image, ImageDraw, ImageFont

from st7735 import ST7735
from stats  import (get_ip, get_cpu_percent, get_ram_info,
                    get_disk_percent, get_disk_gb, get_temperature)
from button import ButtonMonitor

# ── Configuration ───────────────────────────────────────────────────────────

IFACE         = 'end0'    # Pi 5 / HAOS network interface (not eth0 / wlan0)
PAGE_DURATION = 5         # seconds each stats page is shown
NUM_PAGES     = 5         # total number of rotating pages
W, H          = 160, 80   # display pixels

# Colour palette
BLACK  = (0,   0,   0)
WHITE  = (255, 255, 255)
GREY   = (100, 100, 100)
GREEN  = (50,  220, 80)
YELLOW = (255, 200, 0)
RED    = (255,  60, 60)
CYAN   = (0,   210, 230)

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('rm0004')

# ── Font helpers ─────────────────────────────────────────────────────────────

def _font(size: int):
    """Load PIL default font at *size*.  Falls back to tiny built-in."""
    try:
        return ImageFont.load_default(size=size)   # Pillow ≥ 10.1
    except TypeError:
        return ImageFont.load_default()            # older Pillow


_FONT_TITLE = _font(11)
_FONT_VALUE = _font(26)
_FONT_SUB   = _font(12)
_FONT_IP    = _font(16)

# ── Page rendering ───────────────────────────────────────────────────────────

def _new_image(bg=BLACK):
    return Image.new('RGB', (W, H), bg)


def _centered_x(draw, text, font, width=W):
    """Return x coordinate to centre *text* horizontally."""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return max(0, (width - (bbox[2] - bbox[0])) // 2)
    except AttributeError:
        # Pillow < 8 fallback
        tw, _ = draw.textsize(text, font=font)
        return max(0, (width - tw) // 2)


def _bar(pct: float, width: int = 22) -> str:
    filled = round(pct / 100 * width)
    return '▮' * filled + '▯' * (width - filled)


def page_ip(ip: str) -> Image.Image:
    img  = _new_image()
    draw = ImageDraw.Draw(img)
    draw.text((4, 3),  'NETWORK',  font=_FONT_TITLE, fill=GREY)
    draw.text((4, 18), 'IP',       font=_FONT_SUB,   fill=GREY)
    # IP address — may be long, split if needed
    parts = ip.split('.')
    if len(parts) == 4:
        line1 = '.'.join(parts[:2]) + '.'
        line2 = '.'.join(parts[2:])
        draw.text((4, 34), line1, font=_FONT_IP, fill=CYAN)
        draw.text((4, 54), line2, font=_FONT_IP, fill=CYAN)
    else:
        draw.text((4, 38), ip, font=_FONT_SUB, fill=CYAN)
    draw.text((4, 70), f'iface: {IFACE}', font=_font(9), fill=GREY)
    return img


def page_cpu(pct: float) -> Image.Image:
    img  = _new_image()
    draw = ImageDraw.Draw(img)
    colour = RED if pct > 85 else YELLOW if pct > 60 else GREEN
    draw.text((4, 3), 'CPU', font=_FONT_TITLE, fill=GREY)
    val = f'{pct:.1f}%'
    draw.text((_centered_x(draw, val, _FONT_VALUE), 16), val,
              font=_FONT_VALUE, fill=colour)
    bar = _bar(pct)
    draw.text((_centered_x(draw, bar, _FONT_SUB), 56), bar,
              font=_FONT_SUB, fill=colour)
    return img


def page_ram(used_gb: float, total_gb: float, pct: float) -> Image.Image:
    img  = _new_image()
    draw = ImageDraw.Draw(img)
    colour = RED if pct > 85 else YELLOW if pct > 70 else GREEN
    draw.text((4, 3), 'RAM', font=_FONT_TITLE, fill=GREY)
    val = f'{pct:.1f}%'
    draw.text((_centered_x(draw, val, _FONT_VALUE), 16), val,
              font=_FONT_VALUE, fill=colour)
    sub = f'{used_gb:.1f} / {total_gb:.1f} GB'
    draw.text((_centered_x(draw, sub, _FONT_SUB), 56), sub,
              font=_FONT_SUB, fill=GREY)
    return img


def page_disk(pct: float, used_gb: float, total_gb: float) -> Image.Image:
    img  = _new_image()
    draw = ImageDraw.Draw(img)
    colour = RED if pct > 90 else YELLOW if pct > 75 else GREEN
    draw.text((4, 3), 'DISK', font=_FONT_TITLE, fill=GREY)
    val = f'{pct:.1f}%'
    draw.text((_centered_x(draw, val, _FONT_VALUE), 16), val,
              font=_FONT_VALUE, fill=colour)
    sub = f'{used_gb:.1f} / {total_gb:.1f} GB'
    draw.text((_centered_x(draw, sub, _FONT_SUB), 56), sub,
              font=_FONT_SUB, fill=GREY)
    return img


def page_temp(temp: float) -> Image.Image:
    img  = _new_image()
    draw = ImageDraw.Draw(img)
    colour = RED if temp > 80 else YELLOW if temp > 65 else GREEN
    draw.text((4, 3), 'TEMPERATURE', font=_FONT_TITLE, fill=GREY)
    val = f'{temp:.1f}°C'
    draw.text((_centered_x(draw, val, _FONT_VALUE), 20), val,
              font=_FONT_VALUE, fill=colour)
    if temp > 75:
        warn = '! HIGH TEMP !'
        draw.text((_centered_x(draw, warn, _FONT_SUB), 58), warn,
                  font=_FONT_SUB, fill=RED)
    return img


# ── Shutdown helper ──────────────────────────────────────────────────────────

def _ha_shutdown() -> None:
    """Call Supervisor API to shut down the host, with CLI fallback."""
    token = os.environ.get('SUPERVISOR_TOKEN', '')
    if token:
        try:
            import urllib.request
            req = urllib.request.Request(
                'http://supervisor/host/shutdown',
                method='POST',
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                },
                data=b'{}',
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                log.info("Supervisor shutdown: HTTP %d", resp.status)
                return
        except Exception as exc:
            log.warning("Supervisor API failed (%s), trying CLI", exc)
    # Fallback — available inside HA add-ons that have hassio_api access
    log.info("Falling back to: ha host shutdown")
    os.system('ha host shutdown')


# ── Main loop ────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("UCTRONICS RM0004 add-on starting")

    # Initialise hardware
    display     = ST7735()
    display_on  = True
    running     = True
    page        = 0
    page_ts     = time.monotonic()

    try:
        display.init()
        display.clear(BLACK)
    except Exception as exc:
        log.error("Display init failed: %s", exc)
        sys.exit(1)

    # Button callbacks (called from button thread — keep fast)
    def on_short():
        nonlocal display_on
        display_on = not display_on
        display.set_backlight(display_on)

    def on_long():
        nonlocal running
        log.info("Long press → requesting host shutdown")
        running = False
        _ha_shutdown()

    btn = ButtonMonitor(on_short=on_short, on_long=on_long)
    btn.start()
    log.info("Button monitor started (gpiochip4 offset 4)")

    # Signal handling
    def _sig(sig, _):
        nonlocal running
        log.info("Received signal %d, stopping", sig)
        running = False

    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT,  _sig)

    log.info("Entering display loop (page duration %ds, iface %s)",
             PAGE_DURATION, IFACE)

    while running:
        # ── Advance page on timer ──────────────────────────────────────────
        now = time.monotonic()
        if now - page_ts >= PAGE_DURATION:
            page    = (page + 1) % NUM_PAGES
            page_ts = now

        # ── Collect stats & render ─────────────────────────────────────────
        if display_on:
            try:
                if page == 0:
                    img = page_ip(get_ip(IFACE))

                elif page == 1:
                    # CPU measurement blocks for 0.4 s — factor into timing
                    cpu = get_cpu_percent(interval=0.4)
                    img = page_cpu(cpu)

                elif page == 2:
                    used, total, pct = get_ram_info()
                    img = page_ram(used, total, pct)

                elif page == 3:
                    pct           = get_disk_percent()
                    used, total   = get_disk_gb()
                    img = page_disk(pct, used, total)

                else:   # page == 4
                    img = page_temp(get_temperature())

                display.display(img)

            except Exception as exc:
                log.error("Page %d render/display error: %s", page, exc)

        time.sleep(1)

    # ── Clean up ───────────────────────────────────────────────────────────
    log.info("Shutting down add-on")
    btn.stop()
    try:
        display.clear(BLACK)
        display.close()
    except Exception:
        pass


if __name__ == '__main__':
    main()
