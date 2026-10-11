#!/usr/bin/env bash
# Refuse releases without an independently recorded successful boot.
set -euo pipefail
[[ "$#" -eq 2 ]] || { echo 'Usage: release-gate.sh ISO BOOT_REPORT_JSON' >&2; exit 2; }
python3 - "$1" "$2" <<'PY'
import hashlib, json, pathlib, sys
iso, report = map(pathlib.Path, sys.argv[1:])
if not iso.is_file() or iso.stat().st_size == 0:
    raise SystemExit("FAIL: missing ISO")
if not report.is_file():
    raise SystemExit("FAIL: missing boot report")
data = json.loads(report.read_text())
digest = hashlib.sha256(iso.read_bytes()).hexdigest()
if data.get("iso_sha256") != digest:
    raise SystemExit("FAIL: ISO SHA256 mismatch")
if data.get("qemu_booted") is not True:
    raise SystemExit("FAIL: boot not verified")
if data.get("graphical_session_started") is not True:
    raise SystemExit("FAIL: graphical session not verified")
print("PASS: ISO checksum and reported boot evidence")
PY
