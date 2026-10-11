#!/usr/bin/env bash
# Creates a Debian-based Localzet Live ISO using live-build (not an Ubuntu ISO).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${LOCALZET_BUILD_DIR:-$ROOT/out/localzet-live}"
case "$OUT" in /|"$ROOT"|"$ROOT/"|/etc|/usr|/home) echo "Unsafe build directory: $OUT" >&2; exit 2;; esac
[[ ! -L "$OUT" ]] || { echo "Build directory cannot be a symlink" >&2; exit 2; }
for cmd in lb sudo rsync sha256sum; do command -v "$cmd" >/dev/null || { echo "Missing $cmd" >&2; exit 1; }; done
[[ ! -e "$OUT/config" ]] || { echo "Build directory already configured: $OUT. Remove manually to rebuild." >&2; exit 2; }
"$ROOT/scripts/preflight.sh" --build
mkdir -p "$OUT"
cd "$OUT"
lb config --distribution trixie --architectures amd64 --binary-images iso-hybrid --archive-areas 'main contrib non-free-firmware' --debian-installer none
mkdir -p config/package-lists config/includes.chroot/opt/localzet-os config/hooks/live
cat > config/package-lists/localzet.list.chroot <<'PACKAGES'
linux-image-amd64 live-boot live-config systemd-sysv
labwc foot swaybg lightdm xwayland thunar waybar
network-manager network-manager-gnome dbus-user-session dbus-x11
pipewire pipewire-pulse wireplumber pavucontrol
policykit-1-gnome fonts-dejavu-core fonts-noto-core
xserver-xorg-input-libinput mesa-utils firmware-linux-free
sudo curl ca-certificates bash git xdg-utils xdg-desktop-portal xdg-desktop-portal-gtk
build-essential pkg-config libgtk-4-dev libgtk4-layer-shell-dev rustc cargo
PACKAGES
rsync -a --exclude out --exclude target --exclude .git "$ROOT/" config/includes.chroot/opt/localzet-os/
cat > config/hooks/live/0500-localzet.hook.chroot <<'HOOK'
#!/bin/bash
set -euo pipefail
cd /opt/localzet-os
export CARGO_HOME=/tmp/localzet-cargo
cargo build --release --workspace
install -m755 target/release/localzetd /usr/local/bin/localzetd
install -m755 target/release/localzetctl /usr/local/bin/localzetctl
install -m755 target/release/localzet-desktop /usr/local/bin/localzet-desktop
install -m755 target/release/localzet-panel /usr/local/bin/localzet-panel
install -m755 target/release/localzet-launcher /usr/local/bin/localzet-launcher
install -Dm755 packaging/session/localzet-session /usr/local/bin/localzet-session
install -Dm755 packaging/session/guest-boot-marker /usr/local/bin/localzet-guest-boot-marker
install -Dm644 packaging/session/localzet.desktop /usr/share/wayland-sessions/localzet.desktop
install -Dm644 packaging/applications/localzet-desktop.desktop /usr/share/applications/localzet-desktop.desktop
install -Dm644 packaging/systemd/localzetd.service /etc/systemd/system/localzetd.service
for f in autostart rc.xml; do install -Dm644 "packaging/session/labwc/$f" "/usr/local/share/localzet-os/labwc/$f"; done
for f in config.jsonc style.css; do install -Dm644 "packaging/session/waybar/$f" "/usr/local/share/localzet-os/waybar/$f"; done
systemctl enable localzetd.service
id -u localzet >/dev/null 2>&1 || useradd -m -s /bin/bash -G sudo,audio,video,render,netdev localzet
passwd -l localzet
mkdir -p /etc/lightdm/lightdm.conf.d
printf '[Seat:*]\nautologin-user=localzet\nautologin-user-timeout=0\nuser-session=localzet\n' > /etc/lightdm/lightdm.conf.d/60-localzet.conf
rm -rf /tmp/localzet-cargo /opt/localzet-os/target
HOOK
chmod +x config/hooks/live/0500-localzet.hook.chroot
printf 'Building Debian Trixie based Localzet Live ISO in %s\n' "$OUT"
sudo lb build
find "$OUT" -maxdepth 1 -name '*.iso' -print -exec sha256sum {} \;
( cd "$OUT" && sha256sum ./*.iso > SHA256SUMS )
printf 'Checksums written to %s/SHA256SUMS\n' "$OUT"
