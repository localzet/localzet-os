"""Validate the P6 PPM framebuffer emitted by QEMU's screendump command."""
from pathlib import Path
import re
import time


def is_valid_ppm(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False

    header = re.match(rb"P6\s+(\d+)\s+(\d+)\s+255(?:\r\n|[ \t\n\r])", data)
    if not header:
        return False
    width, height = map(int, header.groups())
    if width < 1 or height < 1:
        return False
    return len(data) - header.end() >= width * height * 3


def wait_for_valid_ppm(path: Path, timeout: float = 10.0, interval: float = 0.1) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        if is_valid_ppm(path):
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(interval, remaining))
