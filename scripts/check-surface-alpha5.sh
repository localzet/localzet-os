#!/usr/bin/env bash
# Compile and stage Localzet Surface components inside an existing live-build chroot.
# Usage: sudo bash scripts/check-surface-alpha5.sh /mnt/localzet-build/live
set -euo pipefail
if [[ ${EUID} -ne 0 ]]; then
  echo "Run as root: sudo bash $0 /mnt/localzet-build/live" >&2
  exit 1
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE="${1:-/mnt/localzet-build/live}"
CHROOT="$LIVE/chroot"
[[ -d "$CHROOT/opt/localzet-os/crates" && -x "$CHROOT/bin/bash" ]] || {
  echo "Invalid Localzet chroot: $CHROOT" >&2
  exit 2
}
for component in localzet-panel localzet-launcher; do
  install -Dm644 "$ROOT/crates/$component/src/main.rs" "$CHROOT/opt/localzet-os/crates/$component/src/main.rs"
done
install -Dm644 "$ROOT/packaging/session/labwc/autostart" "$CHROOT/usr/local/share/localzet-os/labwc/autostart"
chroot "$CHROOT" /bin/bash -c '
  set -euo pipefail
  cd /opt/localzet-os
  export CARGO_HOME=/tmp/localzet-cargo
  cargo build --release -p localzet-panel -p localzet-launcher
'
for component in localzet-panel localzet-launcher; do
  install -m755 "$CHROOT/opt/localzet-os/target/release/$component" "$CHROOT/usr/local/bin/$component"
done
sha256sum "$CHROOT/usr/local/bin/localzet-panel" "$CHROOT/usr/local/bin/localzet-launcher"
echo "Alpha 5 components compiled and staged; ISO was not rebuilt."
