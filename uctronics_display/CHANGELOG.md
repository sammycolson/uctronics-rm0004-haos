# Changelog — UCTRONICS RM0004 Display

## [1.0.2] — 2026-05-10

### Fixed
- `run.sh`: removed i2cdetect probe — `grep` returned exit 1 when 0x18 not found, which combined with bashio's `set -o pipefail` killed the script before Python could start
- `run.sh`: use explicit `/usr/bin/python3` path; stripped to minimum to eliminate all potential bail-out points

## [1.0.1] — 2026-05-10

### Fixed
- `run.sh`: added `2>&1` so Python stderr (tracebacks, import errors) appears in the HA log viewer
- `run.sh`: removed special characters from log strings (encoding safety)
- `config.yaml`: removed `/dev/gpiochip4` from devices list — if the device is absent on the host the supervisor no longer blocks the container start; button.py still opens it by path and fails gracefully
- `display.py`: added early import diagnostics so PIL / smbus2 failures are immediately visible in logs

## [1.0.0] — 2026-05-10

### Added
- Full Python rewrite — no C compilation in container
- Complete ST7735S init sequence via I²C bridge (fixes boot-logo freeze on Pi 5)
- Rotating stats pages: IP (end0), CPU %, RAM %, Disk %, Temperature
- Power button: short press = toggle display, long press ≥ 3 s = HA shutdown
- Pi 5 GPIO support via gpiod v2 (gpiochip4, offset 4)
- Supervisor API shutdown with CLI fallback
- BusyBox-safe stats: `os.statvfs('/')`, `/proc/stat`, `/proc/meminfo`
- No `/dev/sda` or `eth0` assumptions
- Colour-coded values (green / yellow / red) based on load thresholds
- `i2cdetect` sanity check in run.sh with warning if 0x18 not found

### Fixed
- Original C `lcd_begin()` never sent display-init commands → display stuck on boot logo (upstream issue #46)
- Dockerfile ARG had blank default → build error on aarch64
- `df -l` / `grep /dev/sda` incompatible with BusyBox and NVMe boot
