"""Ensure the source gate checks the whole live-boot dependency chain."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SourceGateContract(unittest.TestCase):
    def test_required_files(self):
        gate = (ROOT / "scripts/check-source-tree.sh").read_text()
        for item in (
            "packaging/session/guest-boot-marker",
            "packaging/session/labwc/autostart",
            "packaging/systemd/localzetd.service",
            "packaging/applications/localzet-desktop.desktop",
            "scripts/qemu-graphical-smoke.sh",
            "scripts/validate-iso.sh",
        ):
            self.assertIn(item, gate)

    def test_gate_runs(self):
        result = subprocess.run(
            ["bash", str(ROOT / "scripts/check-source-tree.sh")],
            cwd=ROOT, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rust_binaries_installed(self):
        build = (ROOT / "scripts/build-localzet-live.sh").read_text()
        for name in ("localzetd", "localzetctl", "localzet-desktop", "localzet-panel", "localzet-launcher"):
            self.assertIn(f"target/release/{name}", build)
