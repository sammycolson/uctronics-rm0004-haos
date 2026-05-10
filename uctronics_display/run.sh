#!/usr/bin/with-contenv bashio

# ── Sanity checks ────────────────────────────────────────────────────────────

bashio::log.info "UCTRONICS RM0004 add-on starting"

if [ ! -e /dev/i2c-1 ]; then
    bashio::log.error "/dev/i2c-1 not found — enable I²C in HAOS and reboot"
    exit 1
fi

if [ ! -e /dev/gpiochip4 ]; then
    bashio::log.warning "/dev/gpiochip4 not found — button will be disabled (Pi 4 uses gpiochip0)"
fi

# Verify the UCTRONICS bridge is visible on the I²C bus (address 0x18)
if command -v i2cdetect >/dev/null 2>&1; then
    DETECTED=$(i2cdetect -y 1 2>/dev/null | grep -o '18' | head -1)
    if [ -z "$DETECTED" ]; then
        bashio::log.warning "I²C device 0x18 not detected — check cable / power"
    else
        bashio::log.info "I²C bridge detected at 0x18 ✓"
    fi
fi

# ── Launch ───────────────────────────────────────────────────────────────────

bashio::log.info "Launching display loop"
exec python3 /app/display.py
