#!/usr/bin/env bash
# Проверка наличия полного дерева исходников.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
for item in Cargo.toml README.md LICENSE scripts/build-localzet-live.sh scripts/release-gate.sh; do
  [[ -s "$item" ]] || { echo "MISSING: $item" >&2; exit 1; }
done
for crate in localzet-core localzetd localzetctl localzet-desktop localzet-panel localzet-launcher; do
  [[ -s "crates/$crate/Cargo.toml" ]] || { echo "MISSING crate: $crate" >&2; exit 1; }
  find "crates/$crate/src" -maxdepth 1 -type f -name '*.rs' | grep -q . || { echo "MISSING Rust source: $crate" >&2; exit 1; }
done
echo 'PASS: source tree is structurally complete (not a compile test)'
