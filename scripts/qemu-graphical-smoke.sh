#!/usr/bin/env bash
# Guest serial marker smoke test. This does not verify visible rendering.
set -euo pipefail
ISO="${1:-}"
OUT="${2:-out/qemu-smoke}"
[[ -n "$ISO" && -s "$ISO" ]] || { echo 'Usage: qemu-graphical-smoke.sh ISO [OUT]' >&2; exit 2; }
command -v qemu-system-x86_64 >/dev/null || { echo 'Missing qemu-system-x86_64' >&2; exit 2; }
mkdir -p "$OUT"
set +e
timeout --signal=TERM --kill-after=10s "${LOCALZET_QEMU_TIMEOUT:-240}" \
  qemu-system-x86_64 -machine q35 -m 4096 -smp 4 -display none \
  -serial stdio -monitor none -cdrom "$ISO" -boot d -nic user,model=virtio-net-pci -no-reboot \
  > "$OUT/serial.log" 2>&1
qemu_status=$?
set -e
python3 - "$ISO" "$OUT/serial.log" "$OUT/boot-report.json" "$qemu_status" <<'PY'
import datetime, hashlib, json, pathlib, sys
iso, log, output, code = sys.argv[1:]
iso_sha = hashlib.sha256(pathlib.Path(iso).read_bytes()).hexdigest()
serial = pathlib.Path(log).read_text(encoding='utf-8', errors='replace')
marker = 'LOCALZET_GUI_SESSION_READY_V2'
ready = any(line.strip() == marker for line in serial.splitlines())
report = {
    'schema_version': 1, 'iso_sha256': iso_sha, 'qemu_booted': ready,
    'graphical_session_started': ready,
    'tested_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'tester': 'localzet-qemu-guest-serial-marker-v1',
    'qemu_exit_code': int(code), 'evidence': 'serial.log', 'verified': ready,
}
pathlib.Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print('PASS: guest compositor autostart marker received' if ready else 'FAIL: guest marker absent')
raise SystemExit(0 if ready else 1)
PY
