"""Offline checks for the Debian live-build configuration."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent

class LiveBuilderContract(unittest.TestCase):
    def test_required_desktop_packages(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        for name in ("labwc", "lightdm", "waybar", "wofi", "foot", "thunar", "libgtk4-layer-shell-dev"):
            self.assertIn(name, source)

    def test_guest_marker_installed_and_started(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        autostart = (ROOT / "packaging/session/labwc/autostart").read_text()
        self.assertIn("packaging/session/guest-boot-marker", source)
        self.assertIn("localzet-guest-boot-marker", autostart)

    def test_iso_must_be_unique_and_nonempty(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertIn('images=("$OUT"/*.iso)', source)
        self.assertIn('[[ -s "${images[0]}" ]]', source)

    def test_live_account_is_password_locked(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertIn("passwd -l localzet", source)

    def test_zsh_is_default_and_bash_remains_available(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertIn("bash zsh git", source)
        self.assertIn("useradd -m -s /usr/bin/zsh", source)
        self.assertIn("usermod -s /usr/bin/zsh localzet", source)

    def test_windows_app_compatibility_includes_debian_wine(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertIn("wine wine64", source)

    def test_iso_build_uses_locked_rust_dependencies(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertTrue((ROOT / "Cargo.lock").is_file())
        self.assertIn("cargo build --release --workspace --locked", source)

    def test_unsafe_os_prober_is_not_installed_in_live_image(self):
        source = (ROOT / "scripts/build-localzet-live.sh").read_text()
        self.assertNotIn("python3 os-prober", source)
        self.assertIn("python3 util-linux", source)
