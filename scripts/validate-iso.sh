#!/usr/bin/env bash
# Static ISO validation; does not prove boot or graphical rendering.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO="${1:-$ROOT/out/localzet-ubuntu-26.04/live-image-amd64.hybrid.iso}"
[[ -f "$ISO" && -s "$ISO" ]] || { echo "FAIL: ISO missing or empty: $ISO" >&2; exit 2; }
for cmd in file sha256sum; do command -v "$cmd" >/dev/null || exit 2; done
mime="$(file -b "$ISO")"
case "$mime" in *ISO\ 9660*|*ISO-9660*) ;; *) echo "FAIL: not ISO9660: $mime" >&2; exit 3;; esac
if command -v xorriso >/dev/null; then
  xorriso -indev "$ISO" -find / -name filesystem.squashfs -exec lsdl 2>/dev/null | grep -q filesystem.squashfs || { echo 'FAIL: squashfs missing' >&2; exit 4; }
else
  echo 'WARN: xorriso missing; filesystem contents not inspected' >&2
fi
sha256sum "$ISO"
echo 'PASS: static ISO check only'
