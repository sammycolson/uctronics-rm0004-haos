"""
System stats for HAOS on Raspberry Pi 5.

All reads are Python-native: no shell commands, no GNU-specific flags,
fully BusyBox-safe.  Disk usage uses os.statvfs('/') — no /dev/sda
assumption.  Network IP is read via socket ioctl for the specific
interface (defaults to 'end0' which is what Pi 5 / HAOS uses).
"""

import os
import socket
import struct
import fcntl
import time
import logging

log = logging.getLogger(__name__)

# ── IP address ──────────────────────────────────────────────────────────────

_SIOCGIFADDR = 0x8915   # Linux ioctl to get interface IPv4 address


def get_ip(iface: str = 'end0') -> str:
    """Return IPv4 address of *iface*, or 'N/A' on failure."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            packed = struct.pack('256s', iface.encode()[:15])
            result = fcntl.ioctl(s.fileno(), _SIOCGIFADDR, packed)
            return socket.inet_ntoa(result[20:24])
    except OSError:
        return 'N/A'
    except Exception as exc:
        log.debug("get_ip(%s): %s", iface, exc)
        return 'N/A'


# ── CPU usage ───────────────────────────────────────────────────────────────

def _cpu_times() -> tuple:
    """Return (idle_jiffies, total_jiffies) from /proc/stat line 'cpu'."""
    with open('/proc/stat') as fh:
        fields = fh.readline().split()   # 'cpu  user nice system idle iowait ...'
    values = [int(x) for x in fields[1:]]
    idle  = values[3] + values[4]       # idle + iowait
    total = sum(values)
    return idle, total


def get_cpu_percent(interval: float = 0.4) -> float:
    """
    Measure CPU usage over *interval* seconds.
    Returns a float in [0, 100].
    """
    idle1, tot1 = _cpu_times()
    time.sleep(interval)
    idle2, tot2 = _cpu_times()
    d_idle  = idle2 - idle1
    d_total = tot2  - tot1
    if d_total == 0:
        return 0.0
    return max(0.0, min(100.0, (1.0 - d_idle / d_total) * 100.0))


# ── RAM usage ───────────────────────────────────────────────────────────────

def get_ram_info() -> tuple:
    """
    Return (used_gb, total_gb, pct_used) from /proc/meminfo.
    Values are float; pct_used in [0, 100].
    """
    mem = {}
    with open('/proc/meminfo') as fh:
        for line in fh:
            parts = line.split()
            if parts[0] in ('MemTotal:', 'MemAvailable:'):
                mem[parts[0]] = int(parts[1])   # kB
                if len(mem) == 2:
                    break
    total_kb = mem.get('MemTotal:',     0)
    avail_kb = mem.get('MemAvailable:', 0)
    used_kb  = total_kb - avail_kb
    if total_kb == 0:
        return 0.0, 0.0, 0.0
    return (used_kb  / 1_048_576,      # → GB  (1 GB = 1 048 576 kB)
            total_kb / 1_048_576,
            used_kb  / total_kb * 100.0)


# ── Disk usage ──────────────────────────────────────────────────────────────

def get_disk_percent() -> float:
    """
    Return root filesystem usage percentage via os.statvfs('/').
    BusyBox-safe; no /dev/sda or 'df -l' assumptions.
    """
    try:
        st    = os.statvfs('/')
        total = st.f_blocks * st.f_frsize
        free  = st.f_bavail * st.f_frsize
        if total == 0:
            return 0.0
        return (total - free) / total * 100.0
    except Exception as exc:
        log.debug("get_disk_percent: %s", exc)
        return 0.0


def get_disk_gb() -> tuple:
    """Return (used_gb, total_gb) for '/'."""
    try:
        st    = os.statvfs('/')
        total = st.f_blocks * st.f_frsize
        free  = st.f_bavail * st.f_frsize
        return (total - free) / 1e9, total / 1e9
    except Exception:
        return 0.0, 0.0


# ── Temperature ─────────────────────────────────────────────────────────────

_TEMP_PATHS = [
    '/sys/class/thermal/thermal_zone0/temp',   # standard
    '/sys/class/thermal/thermal_zone1/temp',   # Pi 5 sometimes uses zone1
    '/sys/class/hwmon/hwmon0/temp1_input',
]


def get_temperature() -> float:
    """Return SoC temperature in °C, or 0.0 on failure."""
    for path in _TEMP_PATHS:
        try:
            with open(path) as fh:
                return int(fh.read().strip()) / 1000.0
        except (OSError, ValueError):
            continue
    return 0.0
