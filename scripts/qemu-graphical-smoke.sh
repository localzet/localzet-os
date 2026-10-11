#!/usr/bin/env bash
# Observe a guest boot; stop QEMU when the complete V2 marker arrives.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO="${1:-}"
OUT="${2:-$ROOT/out/qemu-smoke}"
[[ -n "$ISO" && -s "$ISO" ]] || { echo 'Usage: qemu-graphical-smoke.sh ISO [OUT]' >&2; exit 2; }
for cmd in qemu-system-x86_64 python3; do command -v "$cmd" >/dev/null || { echo "Missing $cmd" >&2; exit 2; }; done
mkdir -p "$OUT"
python3 - "$ISO" "$OUT" <<'PYCODE'
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

iso = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
log = out / 'serial.log'
report_path = out / 'boot-report.json'
marker = b'LOCALZET_GUI_SESSION_READY_V2'
timeout = int(os.environ.get('LOCALZET_QEMU_TIMEOUT', '240'))
if not 1 <= timeout <= 3600:
    raise SystemExit('LOCALZET_QEMU_TIMEOUT must be 1..3600 seconds')
command = ['qemu-system-x86_64', '-machine', 'q35', '-m', '4096', '-smp', '4',
           '-display', 'none', '-serial', 'stdio', '-monitor', 'none',
           '-cdrom', str(iso), '-boot', 'd', '-nic', 'user,model=virtio-net-pci', '-no-reboot']
with iso.open('rb') as stream:
    sha = hashlib.file_digest(stream, 'sha256').hexdigest()
ready = False
started = time.monotonic()
with log.open('wb') as stream:
    process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL)
    try:
        while time.monotonic() - started < timeout:
            if log.exists():
                ready = marker in log.read_bytes().splitlines()
                if ready:
                    break
            if process.poll() is not None:
                break
            time.sleep(1)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
report = {
    'schema_version': 1, 'iso_sha256': sha, 'qemu_booted': ready,
    'graphical_session_started': ready, 'verified': ready,
    'tested_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'tester': 'localzet-qemu-guest-serial-marker-v2',
    'qemu_exit_code': process.returncode, 'evidence': 'serial.log',
    'elapsed_seconds': round(time.monotonic() - started, 1),
}
report_path.write_text(json.dumps(report, indent=2) + '\n')
print('PASS: guest panel and desktop process marker' if ready else 'FAIL: marker absent')
print('Evidence:', report_path)
raise SystemExit(0 if ready else 1)
PYCODE
