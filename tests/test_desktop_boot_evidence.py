"""Contract tests for desktop boot evidence."""
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_qemu_screen import is_valid_ppm, wait_for_valid_ppm

class DesktopBootEvidence(unittest.TestCase):
    def test_marker_requires_panel(self):
        source = (ROOT / "packaging/session/guest-boot-marker").read_text()
        self.assertIn("if process_running localzet-panel;", source)
        self.assertNotIn("process_running localzet-desktop", source)
        self.assertIn("LOCALZET_GUI_SESSION_READY_V3", source)
        self.assertNotIn("LOCALZET_GUI_SESSION_READY_V1", source)

    def test_qemu_requires_v3(self):
        source = (ROOT / "scripts/qemu-graphical-smoke.sh").read_text()
        self.assertIn("LOCALZET_GUI_SESSION_READY_V3", source)
        self.assertIn("verified': ready and screen_captured", source)
        self.assertIn("screen_captured", source)
        self.assertIn("wait_for_valid_ppm(screenshot)", source)

    def test_screenshot_validator_rejects_missing_and_truncated_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            frame = Path(directory) / "screen.ppm"
            frame.write_bytes(b"P6\n2 1\n255\n" + bytes(range(6)))
            self.assertTrue(is_valid_ppm(frame))
            frame.write_bytes(b"P6\n2 1\n255\n" + bytes(range(5)))
            self.assertFalse(is_valid_ppm(frame))
            frame.unlink()
            self.assertFalse(is_valid_ppm(frame))

    def test_screenshot_wait_handles_qemu_write_race(self):
        with tempfile.TemporaryDirectory() as directory:
            frame = Path(directory) / "screen.ppm"

            def delayed_write():
                time.sleep(0.03)
                frame.write_bytes(b"P6\n2 1\n255\n" + bytes(range(6)))

            writer = threading.Thread(target=delayed_write)
            writer.start()
            try:
                self.assertTrue(wait_for_valid_ppm(frame, timeout=0.5, interval=0.01))
            finally:
                writer.join()

    def test_release_gate_requires_screenshot(self):
        source = (ROOT / "scripts/release-gate.sh").read_text()
        self.assertIn('data.get("screenshot_captured") is not True', source)
        self.assertIn("is_valid_ppm", source)

    def test_session_logs(self):
        source = (ROOT / "packaging/session/labwc/autostart").read_text()
        self.assertIn("panel.log", source)
        self.assertNotIn("desktop.log", source)
        self.assertNotIn("localzet-desktop >", source)
