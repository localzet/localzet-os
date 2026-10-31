#!/usr/bin/env bash
# Creates an Ubuntu 26.04 GNOME based Localzet Live ISO using live-build.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${LOCALZET_BUILD_DIR:-$ROOT/out/localzet-ubuntu-26.04}"
case "$OUT" in /|"$ROOT"|"$ROOT/"|/etc|/usr|/home) echo "Unsafe build directory: $OUT" >&2; exit 2;; esac
[[ ! -L "$OUT" ]] || { echo "Build directory cannot be a symlink" >&2; exit 2; }
for cmd in lb sudo rsync sha256sum; do command -v "$cmd" >/dev/null || { echo "Missing $cmd" >&2; exit 1; }; done
[[ ! -e "$OUT/config" ]] || { echo "Build directory already configured: $OUT. Remove manually to rebuild." >&2; exit 2; }
bash "$ROOT/scripts/preflight.sh" --build
mkdir -p "$OUT"
cd "$OUT"
lb config --mode ubuntu --mirror-bootstrap https://archive.ubuntu.com/ubuntu --mirror-chroot https://archive.ubuntu.com/ubuntu --mirror-binary https://archive.ubuntu.com/ubuntu --mirror-chroot-security https://security.ubuntu.com/ubuntu --mirror-binary-security https://security.ubuntu.com/ubuntu --distribution resolute --security true --architectures amd64 --linux-packages linux-image --linux-flavours generic --binary-images iso-hybrid --archive-areas 'main restricted universe multiverse' --apt-recommends false --debian-installer false --bootappend-live "boot=casper username=localzet hostname=localzet console=tty0 console=ttyS0,115200n8"
# genisoimage otherwise cannot represent the >4 GiB squashfs in ISO-9660.
printf '\nLB_BOOTLOADER="grub2"\nGENISOIMAGE_OPTIONS_EXTRA="--allow-limited-size"\n' >> config/binary
mkdir -p config/package-lists config/includes.chroot/opt/localzet-os config/hooks
cat > config/package-lists/localzet.list.chroot <<'PACKAGES'
linux-image-generic casper ubuntu-desktop-minimal
nautilus ptyxis epiphany-browser gnome-calculator gnome-text-editor loupe gnome-disk-utility gnome-system-monitor
gnome-software gnome-software-plugin-deb gnome-software-plugin-snap update-manager update-notifier xdg-desktop-portal-gnome
epiphany-browser
network-manager network-manager-gnome pipewire-pulse wireplumber pavucontrol xwayland
fonts-ubuntu fonts-noto-core fonts-noto-color-emoji language-pack-ru language-pack-gnome-ru locales yaru-theme-gtk yaru-theme-icon
zsh bash git curl ca-certificates sudo python3 util-linux mtools libguestfs-tools supermin linux-image-generic
wine wine64 snapd gnome-shell-extension-gsconnect libreoffice-gnome libreoffice-writer libreoffice-calc xdg-utils
build-essential pkg-config libgtk-4-dev rustc cargo librsvg2-bin syslinux-utils
PACKAGES
rsync -a --exclude out --exclude iso-build --exclude iso-artifact --exclude qemu-smoke --exclude target --exclude .git --exclude __pycache__ --exclude "*.pyc" "$ROOT/" config/includes.chroot/opt/localzet-os/
cat > config/hooks/0500-localzet.chroot <<'HOOK'
#!/bin/bash
set -euo pipefail
cd /opt/localzet-os
export CARGO_HOME=/tmp/localzet-cargo
cargo build --release --locked -p localzetd -p localzetctl -p localzet-desktop -p localzet-launcher
install -m755 target/release/localzetd /usr/local/bin/localzetd
install -m755 target/release/localzetctl /usr/local/bin/localzetctl
install -m755 target/release/localzet-desktop /usr/local/bin/localzet-desktop
install -m755 target/release/localzet-launcher /usr/local/bin/localzet-launcher
install -d /usr/local/share/localzet-os
rsvg-convert -w 1920 -h 1080 packaging/wallpaper/sunset-mountains.svg -o /usr/local/share/localzet-os/wallpaper.png
install -Dm755 packaging/session/guest-boot-marker /usr/local/bin/localzet-guest-boot-marker
install -Dm644 packaging/gnome/autostart/localzet-guest-boot-marker.desktop /etc/xdg/autostart/localzet-guest-boot-marker.desktop
install -Dm644 packaging/gnome/98-localzet.gschema.override /usr/share/glib-2.0/schemas/98-localzet.gschema.override
glib-compile-schemas --strict /usr/share/glib-2.0/schemas
install -Dm644 packaging/applications/localzet-desktop.desktop /usr/share/applications/localzet-desktop.desktop
install -Dm644 packaging/applications/localzet-launcher.desktop /usr/share/applications/localzet-launcher.desktop
install -Dm644 packaging/systemd/localzetd.service /etc/systemd/system/localzetd.service
systemctl enable localzetd.service
locale-gen ru_RU.UTF-8
update-locale LANG=ru_RU.UTF-8
cat >> /etc/adduser.conf <<'ADDUSER'
DSHELL=/usr/bin/zsh
EXTRA_GROUPS="adm cdrom sudo dip plugdev users lpadmin dialout audio video render"
ADD_EXTRA_GROUPS=1
ADDUSER
rm -rf /tmp/localzet-cargo /opt/localzet-os/target
apt-get clean
rm -rf /var/lib/apt/lists/*
HOOK
chmod +x config/hooks/0500-localzet.chroot
printf 'Building Ubuntu 26.04 GNOME based Localzet Live ISO in %s\n' "$OUT"
sudo env MKSQUASHFS_OPTIONS="-comp xz -b 1M -Xbcj x86" lb build
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
