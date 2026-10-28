import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "installer_preflight", ROOT / "scripts/installer-preflight.py"
)
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


class InstallerPreflightTests(unittest.TestCase):
    def sample_inventory(self):
        return {
            "read_only": True,
            "boot_mode": "UEFI",
            "intel_vmd_module_loaded": False,
            "intel_vmd_controllers": [],
            "os_probe": {
                "status": "complete",
                "systems": [{"partition": "/dev/testp2", "name": "Windows Boot Manager", "family": "Windows", "boot_method": "efi"}],
            },
            "disks": [{
                "path": "/dev/test", "read_only": False,
                "partitions": [
                    {"path": "/dev/testp1", "filesystem": "vfat", "parttype": PREFLIGHT.EFI_SYSTEM_GUID, "uuid": "esp", "label": "EFI", "mountpoints": []},
                    {"path": "/dev/testp2", "filesystem": "ntfs", "parttype": None, "uuid": "windows", "label": "Windows", "mountpoints": []},
                    {"path": "/dev/testp3", "filesystem": None, "parttype": None, "uuid": None, "label": None, "mountpoints": []},
                ],
            }],
        }

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
        self.assertIn("Установленные системы", report)
        self.assertIn("Накопители не обнаружены", report)

    def test_os_probe_is_disabled_until_a_safe_scanner_exists(self):
        runner = Mock()
        result = PREFLIGHT.probe_installed_systems()
        runner.assert_not_called()
        self.assertEqual(result["status"], "not_implemented_safe_scan")

    @unittest.skipUnless(
        shutil.which("sfdisk") and shutil.which("blkid") and shutil.which("mkfs.ext4"),
        "sfdisk, blkid, and mkfs.ext4 are required for the image integration test",
    )
    def test_disk_image_inspection_reads_gpt_without_mounting(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "fixture.img"
            with image.open("wb") as stream:
                stream.truncate(64 * 1024 * 1024)
            subprocess.run(
                ["sfdisk", str(image)],
                input="label: gpt\nunit: sectors\n\n,32768,L\n",
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["mkfs.ext4", "-F", "-q", "-L", "UbuntuTest", "-E", "offset=1048576", str(image), "16384"],
                check=True,
                capture_output=True,
                text=True,
            )
            result = PREFLIGHT.inspect_disk_image(image)
        self.assertTrue(result["read_only"])
        self.assertEqual(result["label"], "gpt")
        self.assertEqual(len(result["partitions"]), 1)
        self.assertEqual(result["partitions"][0]["filesystem"], "ext4")
        self.assertEqual(result["partitions"][0]["filesystem_label"], "UbuntuTest")
        self.assertEqual(result["os_detection"], "efi_bootloader_evidence_only")

    @unittest.skipUnless(
        shutil.which("sfdisk") and shutil.which("blkid") and shutil.which("mkfs.vfat")
        and shutil.which("mmd") and shutil.which("mcopy"),
        "sfdisk, blkid, mtools, and mkfs.vfat are required for the EFI image test",
    )
    def test_disk_image_reports_efi_bootloader_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "fixture.img"
            esp = root / "esp.img"
            marker = root / "bootmgfw.efi"
            ubuntu_marker = root / "shimx64.efi"
            image.write_bytes(bytes(64 * 1024 * 1024))
            with esp.open("wb") as stream:
                stream.truncate(16 * 1024 * 1024)
            marker.write_bytes(b"test efi marker")
            ubuntu_marker.write_bytes(b"test ubuntu efi marker")
            subprocess.run(
                ["sfdisk", str(image)],
                input=("label: gpt\nunit: sectors\n\n"
                       ",32768,C12A7328-F81F-11D2-BA4B-00A0C93EC93B\n"),
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(["mkfs.vfat", "-F", "16", str(esp)], check=True, capture_output=True)
            for path in ("::/EFI", "::/EFI/Microsoft", "::/EFI/Microsoft/Boot", "::/EFI/ubuntu"):
                subprocess.run(["mmd", "-i", str(esp), path], check=True, capture_output=True)
            subprocess.run(
                ["mcopy", "-i", str(esp), str(marker), "::/EFI/Microsoft/Boot/bootmgfw.efi"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["mcopy", "-i", str(esp), str(ubuntu_marker), "::/EFI/ubuntu/shimx64.efi"],
                check=True,
                capture_output=True,
            )
            with image.open("r+b") as target, esp.open("rb") as source:
                target.seek(1024 * 1024)
                target.write(source.read())
            result = PREFLIGHT.inspect_disk_image(image)
        self.assertEqual(result["partitions"][0]["filesystem"], "vfat")
        self.assertEqual(
            result["partitions"][0]["efi_bootloader_evidence"],
            ["Windows Boot Manager", "Ubuntu EFI bootloader"],
        )
        self.assertEqual(result["os_detection"], "efi_bootloader_evidence_only")

    def test_disk_image_inspection_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "image.img"
            image.touch()
            link = Path(directory) / "link.img"
            link.symlink_to(image)
            with self.assertRaisesRegex(ValueError, "not a symlink"):
                PREFLIGHT.inspect_disk_image(link)

    def test_disk_image_inspection_rejects_partition_outside_image(self):
        runner = Mock(return_value=SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"partitiontable": {
                "label": "gpt", "sectorsize": 512,
                "partitions": [{"start": 200000, "size": 4096}],
            }}),
            stderr="",
        ))
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "image.img"
            image.write_bytes(bytes(1024))
            with self.assertRaisesRegex(ValueError, "extends beyond"):
                PREFLIGHT.inspect_disk_image(image, run=runner)
        runner.assert_called_once()

    def test_guestfs_xml_reports_os_details_without_inferencing_from_filesystem(self):
        runner = Mock(return_value=SimpleNamespace(
            returncode=0,
            stderr="",
            stdout=(
                "<operatingsystems><operatingsystem><name>linux</name>"
                "<distro>ubuntu</distro><product_name>Ubuntu 24.04 LTS</product_name>"
                "<major_version>24</major_version><minor_version>04</minor_version>"
                "<arch>x86_64</arch><root>/dev/sda3</root>"
                "</operatingsystem></operatingsystems>"
            ),
        ))
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "image.img"
            image.touch()
            result = PREFLIGHT.inspect_image_operating_systems(image, run=runner)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["systems"][0]["distro"], "ubuntu")
        self.assertEqual(result["systems"][0]["root_device"], "/dev/sda3")
        self.assertIn("--format=raw", runner.call_args.args[0])

    def test_install_plan_preserves_os_and_efi_and_cannot_execute(self):
        plan = PREFLIGHT.build_install_plan(
            self.sample_inventory(), "/dev/testp3", "/dev/testp1", confirm_format=True
        )
        self.assertEqual(plan["preserve_partitions"], ["/dev/testp1", "/dev/testp2"])
        self.assertFalse(plan["efi_format"])
        self.assertFalse(plan["executable"])
        self.assertTrue(plan["preview_only"])

    def test_install_plan_rejects_os_partition_and_requires_explicit_format(self):
        inventory = self.sample_inventory()
        with self.assertRaisesRegex(ValueError, "operating system"):
            PREFLIGHT.build_install_plan(inventory, "/dev/testp2", "/dev/testp1", confirm_format=True)
        with self.assertRaisesRegex(ValueError, "explicit preview confirmation"):
            PREFLIGHT.build_install_plan(inventory, "/dev/testp3", "/dev/testp1")

    def test_install_plan_rejects_existing_data_filesystems(self):
        inventory = self.sample_inventory()
        inventory["disks"][0]["partitions"][2]["filesystem"] = "ntfs"
        with self.assertRaisesRegex(ValueError, "Existing data and EFI partitions"):
            PREFLIGHT.build_install_plan(inventory, "/dev/testp3", "/dev/testp1", confirm_format=True)

    def test_install_plan_rejects_live_media_and_mounted_targets(self):
        inventory = self.sample_inventory()
        inventory["disks"][0]["partitions"][0]["mountpoints"] = ["/run/live/medium"]
        with self.assertRaisesRegex(ValueError, "live installation medium"):
            PREFLIGHT.build_install_plan(inventory, "/dev/testp3", "/dev/testp1", confirm_format=True)

        inventory = self.sample_inventory()
        inventory["disks"][0]["partitions"][2]["mountpoints"] = ["/media/data"]
        with self.assertRaisesRegex(ValueError, "Mounted partitions"):
            PREFLIGHT.build_install_plan(inventory, "/dev/testp3", "/dev/testp1", confirm_format=True)

    def test_install_plan_rejects_unscanned_systems(self):
        inventory = self.sample_inventory()
        inventory["os_probe"]["status"] = "not_implemented_safe_scan"
        with self.assertRaisesRegex(ValueError, "were not scanned"):
            PREFLIGHT.build_install_plan(inventory, "/dev/testp3", "/dev/testp1", confirm_format=True)


if __name__ == "__main__":
    unittest.main()
