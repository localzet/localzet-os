from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]

class AlphaBootWiring(unittest.TestCase):
    def test_live_user_can_access_serial(self):
        script = (ROOT / 'scripts/build-localzet-live.sh').read_text()
        self.assertIn('dialout audio video render', script)
        self.assertIn('console=ttyS0,115200n8', script)

    def test_one_command_smoke(self):
        script = (ROOT / 'scripts/alpha-build-and-test.sh').read_text()
        for name in ('build-localzet-live.sh', 'qemu-graphical-smoke.sh', 'release-gate.sh'):
            self.assertIn(name, script)

    def test_independent_retest_uses_current_build_artifact(self):
        workflow = (ROOT / '.github/workflows/alpha5-qemu-retest.yml').read_text()
        self.assertIn('workflows: [Ubuntu 26.04 GNOME ISO build and QEMU boot]', workflow)
        self.assertIn('github.event.workflow_run.id || inputs.source_run_id', workflow)
        self.assertNotIn('38389200044', workflow)
