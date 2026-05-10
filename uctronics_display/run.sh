#!/usr/bin/with-contenv bashio

bashio::log.info "UCTRONICS RM0004 Display starting"

if [ ! -e /dev/i2c-1 ]; then
    bashio::log.error "/dev/i2c-1 not found — enable I2C in HAOS config.txt"
    exit 1
fi

bashio::log.info "Launching Python display loop"
exec /usr/bin/python3 -u /app/display.py 2>&1
