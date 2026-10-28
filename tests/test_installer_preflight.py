import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "installer_preflight", ROOT / "scripts/installer-preflight.py"
)
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


class InstallerPreflightTests(unittest.TestCase):
    def test_inventory_is_read_only_and_keeps_data_partition_metadata(self):
        output = {
            "blockdevices": [
                {
                    "name": "/dev/nvme0n1", "type": "disk", "size": 1000,
                    "model": "Test SSD", "tran": "nvme", "rm": False, "ro": False,
                    "children": [{
                        "name": "/dev/nvme0n1p1", "type": "part", "size": 900,
                        "fstype": "ntfs", "label": "Data", "uuid": "data-uuid",
                        "mountpoints": ["/media/data"],
                        "children": [{
                            "name": "/dev/mapper/data", "type": "crypt", "size": 800,
                            "children": [{"name": "/dev/mapper/data-home", "type": "lvm", "size": 700}],
                        }],
                    }],
                },
                {"name": "/dev/loop0", "type": "loop", "size": 10},
            ]
        }
        runner = Mock(return_value=Mock(stdout=json.dumps(output)))
        with tempfile.TemporaryDirectory() as directory:
            sys_root = Path(directory)
            (sys_root / "firmware/efi").mkdir(parents=True)
            (sys_root / "module/vmd").mkdir(parents=True)
            inventory = PREFLIGHT.collect_inventory(runner, sys_root)

        command = runner.call_args.args[0]
        self.assertEqual(command[0], "lsblk")
        self.assertIn("--json", command)
        self.assertEqual(inventory["boot_mode"], "UEFI")
        self.assertTrue(inventory["read_only"])
        self.assertEqual(len(inventory["disks"]), 1)
        partition = inventory["disks"][0]["partitions"][0]
        self.assertEqual(partition["label"], "Data")
        self.assertEqual(partition["uuid"], "data-uuid")
        self.assertEqual(partition["mountpoints"], ["/media/data"])
        self.assertEqual(
            [device["type"] for device in inventory["complex_devices"]],
            ["crypt", "lvm"],
        )

    def test_vmd_controller_ids_are_reported_without_scanning_other_devices(self):
        output = {"blockdevices": []}
        runner = Mock(return_value=Mock(stdout=json.dumps(output)))
        with tempfile.TemporaryDirectory() as directory:
            sys_root = Path(directory)
            driver = sys_root / "bus/pci/drivers/vmd"
            driver.mkdir(parents=True)
            (driver / "0000:00:0e.0").touch()
            inventory = PREFLIGHT.collect_inventory(runner, sys_root)
        self.assertEqual(inventory["intel_vmd_controllers"], ["0000:00:0e.0"])

    def test_report_never_claims_os_detection_or_installation(self):
        report = PREFLIGHT.format_report({
            "boot_mode": "Legacy BIOS",
            "intel_vmd_module_loaded": False,
            "intel_vmd_controllers": [],
            "disks": [],
            "complex_devices": [],
        })
        self.assertIn("ТОЛЬКО ЧТЕНИЕ", report)
        self.assertIn("Распознавание установленных ОС", report)
        self.assertIn("Накопители не обнаружены", report)


if __name__ == "__main__":
    unittest.main()
