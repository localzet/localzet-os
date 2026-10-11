#!/usr/bin/env bash
# Serial-only QEMU observation, NOT graphical boot verification.
set -euo pipefail
ISO="${1:-}"
OUT="${2:-out/boot-evidence}"
[[ -n "$ISO" && -s "$ISO" ]] || { echo 'Usage: boot-evidence.sh ISO [OUT]' >&2; exit 2; }
command -v qemu-system-x86_64 >/dev/null || exit 2
mkdir -p "$OUT"
set +e
timeout --signal=TERM --kill-after=10s "${LOCALZET_QEMU_TIMEOUT:-180}" \
  qemu-system-x86_64 -machine q35 -m 4096 -smp 4 -display none \
  -serial stdio -monitor none -cdrom "$ISO" -boot d -nic user,model=virtio-net-pci \
  -no-reboot > "$OUT/serial.log" 2>&1
status=$?
set -e
python3 - "$ISO" "$OUT/serial.log" "$OUT/boot-report.json" "$status" <<'PY'
import datetime, hashlib, json, pathlib, sys
iso, log, dest, status = sys.argv[1:]
sha = hashlib.sha256(pathlib.Path(iso).read_bytes()).hexdigest()
report = dict(schema_version=1, iso_sha256=sha, qemu_exit_code=int(status),
              tested_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              tester='qemu-serial-observer', qemu_booted=False,
              graphical_session_started=False, verified=False,
              serial_log_bytes=pathlib.Path(log).stat().st_size)
pathlib.Path(dest).write_text(json.dumps(report, indent=2) + '\n')
PY
echo 'Observation saved; graphical boot is NOT verified.'
exit 1
