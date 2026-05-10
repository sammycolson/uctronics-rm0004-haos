#!/usr/bin/with-contenv bashio

bashio::log.info "UCTRONICS RM0004 add-on starting"

# ── Sanity checks ─────────────────────────────────────────────────────────────

if [ ! -e /dev/i2c-1 ]; then
    bashio::log.error "/dev/i2c-1 not found — enable I2C in HAOS and reboot"
    exit 1
fi

if [ ! -e /dev/gpiochip4 ]; then
    bashio::log.warning "/dev/gpiochip4 not found — button disabled"
fi

# Quick I2C probe (non-fatal)
if command -v i2cdetect >/dev/null 2>&1; then
    DETECTED=$(i2cdetect -y 1 2>/dev/null | grep -o '18' | head -1)
    if [ -z "$DETECTED" ]; then
        bashio::log.warning "I2C 0x18 not detected — check RM0004 cable/power"
    else
        bashio::log.info "I2C bridge 0x18 found"
    fi
fi

bashio::log.info "Launching Python display loop"

# 2>&1 is critical: routes Python stderr (tracebacks, import errors)
# into the HA log viewer. Without it, crashes are invisible.
exec python3 -u /app/display.py 2>&1
