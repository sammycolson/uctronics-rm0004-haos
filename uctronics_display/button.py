"""
Power-button monitor for UCTRONICS RM0004 on Raspberry Pi 5.

Pi 5 GPIO is exposed through gpiochip4 (RP1 controller), NOT gpiochip0.
The power button is wired to BCM GPIO 4, which is offset 4 on gpiochip4.

Behaviour
─────────
Short press (< 1.5 s): call on_short  → toggle display on/off
Long press  (≥ 3.0 s): call on_long   → initiate HA host shutdown
"""

import threading
import time
import logging
import datetime

log = logging.getLogger(__name__)

CHIP          = '/dev/gpiochip4'   # Pi 5 — NOT gpiochip0
BUTTON_OFFSET = 4                  # BCM GPIO 4
SHORT_MAX     = 1.5                # seconds — max for short press
LONG_MIN      = 3.0                # seconds — min for long press
DEBOUNCE_MS   = 20                 # hardware debounce window


class ButtonMonitor(threading.Thread):
    """Daemon thread that listens for button edge events via libgpiod."""

    def __init__(self, on_short=None, on_long=None):
        super().__init__(daemon=True, name='rm0004-button')
        self._on_short = on_short or (lambda: None)
        self._on_long  = on_long  or (lambda: None)
        self._stop     = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    # ── Thread entry ────────────────────────────────────────────────────────

    def run(self) -> None:
        try:
            import gpiod
        except ImportError:
            log.warning("gpiod not available — button disabled")
            return

        # Detect API version: gpiod ≥ 2 exposes request_lines()
        if hasattr(gpiod, 'request_lines'):
            self._run_v2(gpiod)
        else:
            self._run_v1(gpiod)

    # ── gpiod ≥ 2.0 (pip install gpiod) ────────────────────────────────────

    def _run_v2(self, gpiod) -> None:
        log.info("Button: using gpiod v2 API on %s offset %d",
                 CHIP, BUTTON_OFFSET)
        try:
            line_cfg = gpiod.LineSettings(
                direction=gpiod.line.Direction.INPUT,
                edge_detection=gpiod.line.Edge.BOTH,
                bias=gpiod.line.Bias.PULL_UP,
                debounce_period=datetime.timedelta(milliseconds=DEBOUNCE_MS),
            )
        except Exception:
            # Older 2.x without debounce_period
            line_cfg = gpiod.LineSettings(
                direction=gpiod.line.Direction.INPUT,
                edge_detection=gpiod.line.Edge.BOTH,
                bias=gpiod.line.Bias.PULL_UP,
            )

        try:
            with gpiod.request_lines(
                CHIP,
                consumer='rm0004-button',
                config={BUTTON_OFFSET: line_cfg},
            ) as req:
                self._event_loop_v2(req, gpiod)
        except Exception as exc:
            log.error("Button v2 error: %s", exc)

    def _event_loop_v2(self, req, gpiod) -> None:
        press_t = None
        while not self._stop.is_set():
            if req.wait_edge_events(datetime.timedelta(seconds=1)):
                for ev in req.read_edge_events():
                    t = gpiod.EdgeEvent.Type
                    if ev.event_type == t.FALLING_EDGE:
                        # Button pressed (pull-up → active low → falling)
                        press_t = time.monotonic()
                    elif ev.event_type == t.RISING_EDGE and press_t is not None:
                        duration = time.monotonic() - press_t
                        press_t  = None
                        self._dispatch(duration)

    # ── gpiod < 2.0 (system package, legacy API) ───────────────────────────

    def _run_v1(self, gpiod) -> None:
        log.info("Button: using gpiod v1 API on %s offset %d",
                 CHIP, BUTTON_OFFSET)
        try:
            chip = gpiod.Chip(CHIP)
            line = chip.get_line(BUTTON_OFFSET)
            flags = 0
            try:
                flags = gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
            except AttributeError:
                pass
            line.request(
                consumer='rm0004-button',
                type=gpiod.LINE_REQ_EV_BOTH_EDGES,
                flags=flags,
            )
            press_t = None
            while not self._stop.is_set():
                if line.event_wait(sec=1):
                    ev = line.event_read()
                    if ev.type == gpiod.LineEvent.FALLING_EDGE:
                        press_t = time.monotonic()
                    elif ev.type == gpiod.LineEvent.RISING_EDGE and press_t is not None:
                        duration = time.monotonic() - press_t
                        press_t  = None
                        self._dispatch(duration)
        except Exception as exc:
            log.error("Button v1 error: %s", exc)
        finally:
            try:
                line.release()
                chip.close()
            except Exception:
                pass

    # ── Dispatch ────────────────────────────────────────────────────────────

    def _dispatch(self, duration: float) -> None:
        log.debug("Button released after %.2f s", duration)
        if duration < 0.05:
            return  # ignore noise / bounce
        if duration >= LONG_MIN:
            log.info("Long press (%.1f s) → shutdown", duration)
            self._on_long()
        else:
            log.info("Short press (%.1f s) → toggle display", duration)
            self._on_short()
