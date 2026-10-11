#!/usr/bin/env bash
# Build and boot Localzet Desktop Alpha; do not claim success without evidence.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
for cmd in python3 qemu-system-x86_64 lb sudo rsync; do
    command -v "$cmd" >/dev/null || { echo "Missing: $cmd" >&2; exit 2; }
done
bash scripts/check-source-tree.sh
python3 -m unittest discover -s tests -p 'test_*.py'
bash scripts/verify-release.sh
bash scripts/build-localzet-live.sh
OUT="${LOCALZET_BUILD_DIR:-$ROOT/out/localzet-live}"
shopt -s nullglob
images=("$OUT"/*.iso)
(( ${#images[@]} == 1 )) || { echo 'Expected exactly one ISO' >&2; exit 3; }
bash scripts/validate-iso.sh "${images[0]}"
bash scripts/qemu-graphical-smoke.sh "${images[0]}" "$ROOT/out/qemu-smoke"
bash scripts/release-gate.sh "${images[0]}" "$ROOT/out/qemu-smoke/boot-report.json"
echo "ALPHA SMOKE PASS: ${images[0]}"
