#!/usr/bin/env bash
# Observe a guest boot; stop QEMU when the V3 panel readiness marker arrives.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO="${1:-}"
OUT="${2:-$ROOT/out/qemu-smoke}"
[[ -n "$ISO" && -s "$ISO" ]] || { echo 'Usage: qemu-graphical-smoke.sh ISO [OUT]' >&2; exit 2; }
for cmd in qemu-system-x86_64 python3; do command -v "$cmd" >/dev/null || { echo "Missing $cmd" >&2; exit 2; }; done
mkdir -p "$OUT"
python3 - "$ISO" "$OUT" "$ROOT" <<'PYCODE'
import datetime
import hashlib
import json
import os
import socket
from pathlib import Path
import subprocess
import sys
import time

iso = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
sys.path.insert(0, sys.argv[3])
log = out / 'serial.log'
report_path = out / 'boot-report.json'
monitor_socket = out / 'qemu-monitor.sock'
screenshot = out / 'guest-screen.ppm'
marker = b'LOCALZET_GUI_SESSION_READY_V3'
timeout = int(os.environ.get('LOCALZET_QEMU_TIMEOUT', '240'))
if not 1 <= timeout <= 3600:
    raise SystemExit('LOCALZET_QEMU_TIMEOUT must be 1..3600 seconds')
screenshot.unlink(missing_ok=True)
command = ['qemu-system-x86_64', '-machine', 'q35', '-m', '4096', '-smp', '4',
           '-display', 'none', '-vga', 'std', '-serial', 'stdio',
           '-monitor', f'unix:{monitor_socket},server=on,wait=off',
           '-cdrom', str(iso), '-boot', 'd', '-nic', 'user,model=virtio-net-pci', '-no-reboot']
with iso.open('rb') as stream:
    sha = hashlib.file_digest(stream, 'sha256').hexdigest()
ready = False
screen_captured = False
boot_key_sent = False
started = time.monotonic()
with log.open('wb') as stream:
    process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL)
    try:
        while time.monotonic() - started < timeout:
            # The live ISO boot menu can wait indefinitely in headless QEMU.
            # Select its highlighted default entry via the HMP keyboard interface.
            if not boot_key_sent and time.monotonic() - started >= 8 and monitor_socket.exists():
                try:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as monitor:
                        monitor.settimeout(8)
                        monitor.connect(str(monitor_socket))
                        monitor.recv(4096)
                        monitor.sendall(b'sendkey ret\n')
                        response = monitor.recv(4096)
                        print(f'QEMU boot menu ENTER: {response!r}', flush=True)
                        boot_key_sent = True
                except (OSError, TimeoutError) as error:
                    print(f'QEMU boot key injection failed: {error}', file=sys.stderr)
            if log.exists():
                ready = marker in log.read_bytes()
                if ready:
                    break
            if process.poll() is not None:
                break
            time.sleep(1)
    finally:
        # The serial readiness marker can arrive before the compositor paints its first frame.
        # Allow the panel and wallpaper time to render before capturing visual evidence.
        if ready and process.poll() is None:
            time.sleep(12)
        # Capture the actual VGA framebuffer even when the guest emits no serial output.
        if process.poll() is None and monitor_socket.exists():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as monitor:
                    monitor.settimeout(8)
                    monitor.connect(str(monitor_socket))
                    monitor.recv(4096)
                    monitor.sendall(f"screendump {screenshot}\n".encode())
                    from validate_qemu_screen import wait_for_valid_ppm
                    screen_captured = wait_for_valid_ppm(screenshot)
                    if not screen_captured:
                        print('QEMU screendump is missing or invalid', file=sys.stderr)
                time.sleep(2)
            except (OSError, TimeoutError) as error:
                print(f"QEMU screenshot capture failed: {error}", file=sys.stderr)
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
report = {
    'schema_version': 1, 'iso_sha256': sha, 'qemu_booted': ready,
    'graphical_session_started': ready, 'screenshot_captured': screen_captured,
    'verified': ready and screen_captured,
    'tested_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'tester': 'localzet-qemu-guest-serial-marker-v3',
    'qemu_exit_code': process.returncode, 'evidence': 'serial.log',
    'elapsed_seconds': round(time.monotonic() - started, 1),
    'screen_capture': screenshot.name if screen_captured else None,
    'boot_key_sent': boot_key_sent,
}
report_path.write_text(json.dumps(report, indent=2) + '\n')
print('PASS: guest panel readiness marker and valid screenshot' if ready and screen_captured
      else 'FAIL: readiness marker or valid screenshot missing')
print('Evidence:', report_path)
raise SystemExit(0 if ready and screen_captured else 1)
PYCODE
