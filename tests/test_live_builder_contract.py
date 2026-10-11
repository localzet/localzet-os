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
