"""Проверка формата отчёта безопасности."""
import importlib.util
from pathlib import Path
import unittest

script = Path(__file__).resolve().parents[1] / "scripts" / "security-audit.py"
spec = importlib.util.spec_from_file_location("security_audit", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SecurityAuditTests(unittest.TestCase):
    def test_report(self):
        report = module.checks()
        self.assertEqual(report["assessment"], "inventory_only")
        self.assertIs(report["certified"], False)
        self.assertEqual(len(report["checks"]), 9)
        self.assertTrue(all(type(x["detected"]) is bool for x in report["checks"]))

if __name__ == "__main__":
    unittest.main()
