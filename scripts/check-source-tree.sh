#!/usr/bin/env bash
# Refuse CI success if files required for a Live ISO are missing.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
for item in Cargo.toml README.md LICENSE .github/workflows/ci.yml scripts/build-localzet-live.sh scripts/release-gate.sh; do
  [[ -s "$item" ]] || { echo "MISSING: $item" >&2; exit 1; }
done
for crate in localzet-core localzetd localzetctl localzet-desktop localzet-panel localzet-launcher; do
  [[ -s "crates/$crate/Cargo.toml" ]] || { echo "MISSING crate: $crate" >&2; exit 1; }
  find "crates/$crate/src" -maxdepth 1 -type f -name '*.rs' | grep -q . || { echo "MISSING Rust source: $crate" >&2; exit 1; }
done
for required in \
  packaging/session/guest-boot-marker \
  packaging/gnome/autostart/localzet-guest-boot-marker.desktop \
  packaging/gnome/98-localzet.gschema.override \
  packaging/applications/localzet-launcher.desktop \
  packaging/systemd/localzetd.service \
  packaging/applications/localzet-desktop.desktop \
  scripts/installer-preflight.py \
  scripts/qemu-graphical-smoke.sh \
  scripts/validate-iso.sh \
  scripts/verify-release.sh; do
  [[ -s "$required" ]] || { echo "MISSING packaging: $required" >&2; exit 1; }
done
echo 'PASS: source tree is structurally complete (not a compile test)'
