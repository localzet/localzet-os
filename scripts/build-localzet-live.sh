#!/usr/bin/env bash
# Creates a Debian-based Localzet Live ISO using live-build (not an Ubuntu ISO).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${LOCALZET_BUILD_DIR:-$ROOT/out/localzet-live}"
case "$OUT" in /|"$ROOT"|"$ROOT/"|/etc|/usr|/home) echo "Unsafe build directory: $OUT" >&2; exit 2;; esac
[[ ! -L "$OUT" ]] || { echo "Build directory cannot be a symlink" >&2; exit 2; }
for cmd in lb sudo rsync sha256sum; do command -v "$cmd" >/dev/null || { echo "Missing $cmd" >&2; exit 1; }; done
[[ ! -e "$OUT/config" ]] || { echo "Build directory already configured: $OUT. Remove manually to rebuild." >&2; exit 2; }
bash "$ROOT/scripts/preflight.sh" --build
mkdir -p "$OUT"
cd "$OUT"
lb config --mode debian --mirror-bootstrap https://deb.debian.org/debian --mirror-chroot https://deb.debian.org/debian --mirror-binary https://deb.debian.org/debian --mirror-chroot-security https://security.debian.org/debian-security --mirror-binary-security https://security.debian.org/debian-security --distribution trixie --security false --architectures amd64 --linux-packages linux-image --linux-flavours amd64 --binary-images iso-hybrid --archive-areas 'main contrib non-free-firmware' --debian-installer none --bootappend-live "boot=live config components username=localzet console=tty0 console=ttyS0,115200n8"
mkdir -p config/package-lists config/includes.chroot/opt/localzet-os config/hooks/live config/archives
# The Ubuntu live-build version probes a removed Debian Contents-amd64.gz index
# when it must discover kernel flavours. Pin the flavour above and disable
# auto-selection because linux-image-amd64 is explicitly in our package list.

# Ubuntu-packaged live-build uses the obsolete trixie/updates security suite.
# Supply the correct Debian 13 suite explicitly instead of its generated entry.
printf "%s\n" "deb https://security.debian.org/debian-security trixie-security main contrib non-free-firmware" > config/archives/debian-security.list.chroot
cat > config/package-lists/localzet.list.chroot <<'PACKAGES'
linux-image-amd64 live-boot live-config systemd-sysv
labwc foot swaybg lightdm xwayland thunar waybar wofi
network-manager network-manager-gnome dbus-user-session dbus-x11
pipewire pipewire-pulse wireplumber pavucontrol
lxqt-policykit fonts-dejavu-core fonts-noto-core
xserver-xorg-input-libinput mesa-utils firmware-linux-free
sudo curl ca-certificates bash zsh git python3 os-prober wine wine64 xdg-utils xdg-desktop-portal xdg-desktop-portal-gtk
build-essential pkg-config libgtk-4-dev libgtk4-layer-shell-dev rustc cargo librsvg2-bin
PACKAGES
rsync -a --exclude out --exclude iso-build --exclude iso-artifact --exclude qemu-smoke --exclude target --exclude .git --exclude __pycache__ --exclude "*.pyc" "$ROOT/" config/includes.chroot/opt/localzet-os/
cat > config/hooks/live/0500-localzet.hook.chroot <<'HOOK'
#!/bin/bash
set -euo pipefail
cd /opt/localzet-os
export CARGO_HOME=/tmp/localzet-cargo
cargo build --release --workspace --locked
install -m755 target/release/localzetd /usr/local/bin/localzetd
install -m755 target/release/localzetctl /usr/local/bin/localzetctl
install -m755 target/release/localzet-desktop /usr/local/bin/localzet-desktop
install -m755 target/release/localzet-panel /usr/local/bin/localzet-panel
install -m755 target/release/localzet-launcher /usr/local/bin/localzet-launcher
install -d /usr/local/share/localzet-os
rsvg-convert -w 1920 -h 1080 packaging/wallpaper/sunset-mountains.svg -o /usr/local/share/localzet-os/wallpaper.png
install -Dm755 packaging/session/localzet-session /usr/local/bin/localzet-session
install -Dm755 packaging/session/guest-boot-marker /usr/local/bin/localzet-guest-boot-marker
install -Dm644 packaging/session/localzet.desktop /usr/share/wayland-sessions/localzet.desktop
install -Dm644 packaging/applications/localzet-desktop.desktop /usr/share/applications/localzet-desktop.desktop
install -Dm644 packaging/systemd/localzetd.service /etc/systemd/system/localzetd.service
for f in autostart rc.xml; do install -Dm644 "packaging/session/labwc/$f" "/usr/local/share/localzet-os/labwc/$f"; done
for f in config.jsonc style.css; do install -Dm644 "packaging/session/waybar/$f" "/usr/local/share/localzet-os/waybar/$f"; done
systemctl enable localzetd.service
id -u localzet >/dev/null 2>&1 || useradd -m -s /usr/bin/zsh -G sudo,audio,video,render,netdev,dialout localzet
usermod -s /usr/bin/zsh localzet
# Lock the password for distribution; LightDM uses PAM autologin.
passwd -l localzet
getent group autologin >/dev/null || groupadd autologin
usermod -aG autologin localzet
install -Dm755 packaging/session/localzet-lightdm-session /usr/local/bin/localzet-lightdm-session
install -Dm644 packaging/session/60-localzet.conf /etc/lightdm/lightdm.conf.d/60-localzet.conf
rm -rf /tmp/localzet-cargo /opt/localzet-os/target
HOOK
chmod +x config/hooks/live/0500-localzet.hook.chroot
printf 'Building Debian Trixie based Localzet Live ISO in %s\n' "$OUT"
sudo lb build
shopt -s nullglob
images=("$OUT"/*.iso)
if (( ${#images[@]} != 1 )); then
  echo "Expected exactly one ISO; found ${#images[@]}" >&2
  exit 1
fi
[[ -s "${images[0]}" ]] || { echo "ISO is empty" >&2; exit 1; }
find "$OUT" -maxdepth 1 -name '*.iso' -print -exec sha256sum {} \;
( cd "$OUT" && sha256sum ./*.iso > SHA256SUMS )
printf 'Checksums written to %s/SHA256SUMS\n' "$OUT"
