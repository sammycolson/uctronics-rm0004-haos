# Changelog — UCTRONICS RM0004 Display

## [1.0.0] — 2025-05-10

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
