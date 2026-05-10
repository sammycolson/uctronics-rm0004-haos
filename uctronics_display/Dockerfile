# ── Build argument — MUST have a default for HA OS builder ─────────────────
# (leaving the default blank caused the original fork to fail)
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest
FROM ${BUILD_FROM}

LABEL \
    io.hass.name="UCTRONICS RM0004 Display" \
    io.hass.description="LCD and power-button driver for UCTRONICS RM0004 Pi Rack Pro on Pi 5" \
    io.hass.arch="aarch64" \
    io.hass.type="addon" \
    maintainer="sammycolson"

# ── System dependencies ─────────────────────────────────────────────────────
# python3, pip, i2c-tools (for i2cdetect debugging), libgpiod for the button
RUN apk add --no-cache \
        python3 \
        py3-pip \
        i2c-tools \
        libgpiod \
        jpeg-dev \
        zlib-dev \
        freetype-dev \
        musl-dev \
        gcc \
        python3-dev

# ── Python dependencies ─────────────────────────────────────────────────────
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# ── Application ─────────────────────────────────────────────────────────────
WORKDIR /app
COPY display.py st7735.py stats.py button.py run.sh /app/
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
