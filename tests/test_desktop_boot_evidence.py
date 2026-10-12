"""Contract tests for desktop boot evidence."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]

class DesktopBootEvidence(unittest.TestCase):
    def test_marker_requires_panel(self):
        source = (ROOT / "packaging/session/guest-boot-marker").read_text()
        self.assertIn("if process_running localzet-panel;", source)
        self.assertNotIn("process_running localzet-desktop", source)
        self.assertIn("LOCALZET_GUI_SESSION_READY_V3", source)
        self.assertNotIn("LOCALZET_GUI_SESSION_READY_V1", source)

    def test_qemu_requires_v2(self):
        source = (ROOT / "scripts/qemu-graphical-smoke.sh").read_text()
        self.assertIn("LOCALZET_GUI_SESSION_READY_V3", source)

    def test_session_logs(self):
        source = (ROOT / "packaging/session/labwc/autostart").read_text()
        self.assertIn("panel.log", source)
        self.assertNotIn("desktop.log", source)\n        self.assertNotIn("localzet-desktop >", source)
