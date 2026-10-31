"""Offline checks for the Ubuntu live-build configuration."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent

class LiveBuilderContract(unittest.TestCase):
    def test_iso_validator_uses_supported_xorriso_find_action(self):
        source = (ROOT / "scripts/validate-iso.sh").read_text()
        self.assertIn("-find / -name filesystem.squashfs -exec lsdl", source)
        self.assertNotIn("-find / -name filesystem.squashfs -print", source)

    def test_required_desktop_packages(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        for name in ("casper", "ubuntu-desktop-minimal", "gnome-software", "gnome-software-plugin-deb", "gnome-software-plugin-snap", "ptyxis", "nautilus", "epiphany-browser", "gnome-calculator", "gnome-text-editor", "loupe", "gnome-disk-utility", "libreoffice-writer"):
            self.assertIn(name, source)
        package_block = source.split("<<'PACKAGES'", 1)[1].split("PACKAGES", 1)[0]
        for name in ("labwc", "lightdm", "waybar", "wofi", "thunar", "foot", "live-boot", "live-config"):
            self.assertNotIn(name, package_block)

    def test_live_image_targets_ubuntu_resolute_with_casper_and_gnome(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertIn("--mode ubuntu", source)
        self.assertIn("--distribution resolute", source)
        self.assertIn("--security true", source)
        self.assertIn("--apt-recommends false", source)
        self.assertIn("--debian-installer false", source)
        self.assertNotIn("--debian-installer none", source)
        self.assertIn("boot=casper username=localzet", source)
        self.assertIn("--linux-flavours generic", source)
        self.assertNotIn("--mode debian", source)

    def test_large_hybrid_iso_has_size_support_and_isohybrid_tool(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertIn('GENISOIMAGE_OPTIONS_EXTRA="--allow-limited-size"', source)
        self.assertIn('LB_BOOTLOADER="grub2"', source)
        package_block = source.split("<<'PACKAGES'", 1)[1].split("PACKAGES", 1)[0]
        self.assertIn("syslinux-utils", package_block)

    def test_casper_creates_the_live_user_and_zsh_is_default(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertIn("DSHELL=/usr/bin/zsh", source)
        self.assertIn("dialout", source)
        self.assertNotIn("useradd -m", source)
        self.assertNotIn("passwd -l localzet", source)

    def test_gnome_defaults_match_localzet_desktop_profile(self):
        settings = (ROOT / "packaging/gnome/98-localzet.gschema.override").read_text()
        for value in ("Yaru-magenta-dark", "Yaru-purple-dark", "Ubuntu Sans 11", "prefer-dark", "localzet-launcher.desktop", "org.gnome.Ptyxis.desktop", "ubuntu-dock@ubuntu.com", "('xkb', 'ru')"):
            self.assertIn(value, settings)
        self.assertNotIn("localzet-panel@localzet", settings)

    def test_guest_marker_installed_and_started(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        autostart = (ROOT / "packaging/gnome/autostart/localzet-guest-boot-marker.desktop").read_text()
        self.assertIn("packaging/session/guest-boot-marker", source)
        self.assertIn("Exec=/usr/local/bin/localzet-guest-boot-marker", autostart)

    def test_live_build_hook_uses_supported_root_hook_directory(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertIn("config/hooks/0500-localzet.chroot", source)
        self.assertNotIn("config/hooks/live/", source)

    def test_gnome_launcher_does_not_require_layer_shell_protocol(self):
        manifest = (ROOT / "crates/localzet-launcher/Cargo.toml").read_text()
        source = (ROOT / "crates/localzet-launcher/src/main.rs").read_text()
        self.assertNotIn("gtk4-layer-shell", manifest)
        self.assertNotIn("init_layer_shell", source)
        self.assertIn(".modal(true)", source)

    def test_iso_must_be_unique_and_nonempty(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertIn('images=("$OUT"/*.iso)', source)
        self.assertIn('[[ -s "${images[0]}" ]]', source)
        self.assertIn('sudo env MKSQUASHFS_OPTIONS="-comp xz -b 1M -Xbcj x86" lb build', source)

    def test_live_build_cleans_downloaded_apt_caches_after_installing_packages(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        hook = source.split("cat > config/hooks/0500-localzet.chroot <<'HOOK'", 1)[1].split("\nHOOK", 1)[0]
        self.assertIn("apt-get clean", hook)
        self.assertIn("rm -rf /var/lib/apt/lists/*", hook)

    def test_zsh_is_default_and_bash_remains_available(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertIn("zsh bash git", source)
        self.assertIn("DSHELL=/usr/bin/zsh", source)

    def test_windows_app_compatibility_includes_ubuntu_wine(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertIn("wine wine64", source)

    def test_iso_build_uses_locked_rust_dependencies(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertTrue((ROOT / "Cargo.lock").is_file())
        self.assertIn("cargo build --release --locked -p localzetd", source)

    def test_unsafe_os_prober_is_not_installed_in_live_image(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertNotIn("python3 os-prober", source)
        package_block = source.split("<<'PACKAGES'", 1)[1].split("PACKAGES", 1)[0]
        self.assertIn("python3 util-linux mtools libguestfs-tools", package_block)
