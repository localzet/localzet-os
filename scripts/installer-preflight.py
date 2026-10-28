#!/usr/bin/env python3
"""Read-only storage and firmware inventory for the future installer."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

EFI_SYSTEM_GUID = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"


def probe_installed_systems():
    # os-prober scans every visible disk and may mount partitions; never run it from the desktop.
    return {"status": "not_implemented_safe_scan", "systems": []}


def guest_partition_device(node):
    match = re.search(r"(\d+)$", node or "")
    return f"/dev/sda{match.group(1)}" if match else None


def inspect_disk_image(image_path, run=subprocess.run):
    image = Path(image_path)
    if image.is_symlink() or not image.is_file():
        raise ValueError("Disk image must be an existing regular file, not a symlink or device")
    if not os.access(image, os.R_OK):
        raise ValueError("Disk image is not readable")
    result = run(
        ["sfdisk", "--json", str(image)],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if result.returncode:
        raise ValueError(f"Cannot read partition table: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    table = data.get("partitiontable")
    if not isinstance(table, dict):
        raise ValueError("Partition table data is missing")
    sector_size = table.get("sectorsize")
    if not isinstance(sector_size, int) or sector_size <= 0:
        raise ValueError("Partition table has an invalid sector size")
    image_size = image.stat().st_size
    partitions = []
    for part in table.get("partitions", []):
        start = part.get("start")
        size = part.get("size")
        if not isinstance(start, int) or not isinstance(size, int) or start < 0 or size <= 0:
            raise ValueError("Partition table has invalid partition bounds")
        offset = start * sector_size
        length = size * sector_size
        if offset + length > image_size:
            raise ValueError("Partition extends beyond the disk image")
        probe = run(
            ["blkid", "-p", "-o", "export", "-O", str(offset), "-S", str(length), str(image)],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if probe.returncode not in (0, 2):
            raise ValueError(f"Cannot probe partition filesystem: {probe.stderr.strip()}")
        metadata = dict(
            line.split("=", 1) for line in probe.stdout.splitlines() if "=" in line
        ) if probe.returncode == 0 else {}
        bootloaders = []
        if metadata.get("TYPE") in ("vfat", "fat", "fat32"):
            for label, efi_path in (
                ("Windows Boot Manager", "::/EFI/Microsoft/Boot/bootmgfw.efi"),
                ("Ubuntu EFI bootloader", "::/EFI/ubuntu/shimx64.efi"),
                ("Ubuntu GRUB bootloader", "::/EFI/ubuntu/grubx64.efi"),
            ):
                listing = run(
                    ["mdir", "-i", f"{image}@@{offset}", efi_path],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if listing.returncode == 0:
                    bootloaders.append(label)
        partitions.append({
            "path": part.get("node"),
            "guest_device": guest_partition_device(part.get("node")),
            "start_sector": start,
            "size_sectors": size,
            "type": part.get("type"),
            "uuid": part.get("uuid"),
            "filesystem": metadata.get("TYPE"),
            "filesystem_uuid": metadata.get("UUID"),
            "filesystem_label": metadata.get("LABEL"),
            "efi_bootloader_evidence": bootloaders,
        })
    return {
        "read_only": True,
        "image": str(image.resolve()),
        "label": table.get("label"),
        "sector_size": sector_size,
        "partitions": partitions,
        "os_detection": "not_performed",
        "warning": "Partition tables and filesystem signatures were read without mounting. EFI files are evidence only and do not prove an operating system is installed or bootable.",
    }


def inspect_image_operating_systems(image_path, run=subprocess.run):
    image = Path(image_path)
    if image.is_symlink() or not image.is_file():
        raise ValueError("Disk image must be an existing regular file, not a symlink or device")
    result = run(
        [
            "virt-inspector", "--format=raw", "--no-applications", "--no-icon",
            "--add", str(image),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode:
        return {
            "status": "error",
            "systems": [],
            "error": result.stderr.strip() or "virt-inspector failed",
        }
    try:
        document = ET.fromstring(result.stdout)
    except ET.ParseError as error:
        raise ValueError("virt-inspector returned invalid XML") from error
    systems = []
    for os_node in document.findall("operatingsystem"):
        systems.append({
            "type": os_node.findtext("name"),
            "distro": os_node.findtext("distro"),
            "product_name": os_node.findtext("product_name"),
            "major_version": os_node.findtext("major_version"),
            "minor_version": os_node.findtext("minor_version"),
            "architecture": os_node.findtext("arch"),
            "root_device": os_node.findtext("root"),
        })
    return {"status": "complete" if systems else "none_found", "systems": systems}


def bind_operating_system_partitions(report):
    partitions = {
        partition["guest_device"]: partition["path"]
        for partition in report["partitions"]
        if partition.get("guest_device")
    }
    for system in report.get("operating_systems", {}).get("systems", []):
        root_device = system.get("root_device")
        system["image_root_partition"] = partitions.get(root_device)
        system["partition_match"] = "matched" if root_device in partitions else "unmapped"


def build_install_plan(inventory, target_partition, efi_partition, confirm_format=False):
    if not inventory["read_only"]:
        raise ValueError("Storage inventory is not marked read-only")
    if inventory["boot_mode"] != "UEFI":
        raise ValueError("Preview planning currently supports UEFI only")
    if inventory["os_probe"]["status"] not in ("complete", "none_found"):
        raise ValueError("Installed operating systems were not scanned")

    partitions = {
        part["path"]: (disk, part)
        for disk in inventory["disks"]
        for part in disk["partitions"]
    }
    if target_partition not in partitions:
        raise ValueError("Target must be one of the detected partitions")
    if efi_partition not in partitions:
        raise ValueError("EFI partition must be selected from the detected partitions")

    target_disk, target = partitions[target_partition]
    _, efi = partitions[efi_partition]
    if target_disk["read_only"] or target_partition == efi_partition:
        raise ValueError("Target partition is not writable or conflicts with the EFI partition")
    target_type = (target.get("parttype") or "").lower()
    if target["mountpoints"]:
        raise ValueError("Mounted partitions cannot be selected for formatting")
    if target_partition in {system["partition"] for system in inventory["os_probe"]["systems"]}:
        raise ValueError("A partition containing a detected operating system cannot be selected")
    if target_type in (EFI_SYSTEM_GUID, "0xef") or target.get("filesystem") in ("ntfs", "vfat", "fat", "fat32"):
        raise ValueError("Existing data and EFI partitions cannot be formatting targets in this preview")
    if not confirm_format:
        raise ValueError("Formatting requires an explicit preview confirmation")
    live_mounts = {"/run/live/medium", "/lib/live/mount/medium", "/cdrom", "/isodevice"}
    if any(
        mountpoint in live_mounts
        for part in target_disk["partitions"]
        for mountpoint in part["mountpoints"]
    ):
        raise ValueError("The live installation medium cannot be an installation target")

    efi_type = (efi.get("parttype") or "").lower()
    if efi_type not in (EFI_SYSTEM_GUID, "0xef") or efi.get("filesystem") not in ("vfat", "fat", "fat32"):
        raise ValueError("Selected EFI partition is not a recognized FAT EFI System Partition")
    if efi["mountpoints"]:
        raise ValueError("Mounted EFI partitions cannot be selected")

    preserved = [
        part["path"]
        for disk in inventory["disks"]
        for part in disk["partitions"]
        if part["path"] != target_partition
    ]
    return {
        "preview_only": True,
        "executable": False,
        "target_partition": target_partition,
        "format_as": "ext4",
        "mountpoint": "/",
        "preserve_partitions": preserved,
        "efi_partition": efi_partition,
        "efi_mountpoint": "/boot/efi",
        "efi_format": False,
        "bootloader_target": "UEFI entry in the selected EFI System Partition",
        "os_probe_status": inventory["os_probe"]["status"],
        "warning": "Preview only. The selected partition will be formatted; partition writes and bootloader changes are not implemented.",
    }


def collect_inventory(run=subprocess.run, sys_root=Path("/sys")):
    result = run(
        [
            "lsblk", "--json", "--bytes", "--paths", "--output",
            "NAME,TYPE,SIZE,MODEL,TRAN,RM,RO,FSTYPE,LABEL,UUID,PARTTYPE,MOUNTPOINTS,PKNAME",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    block_devices = json.loads(result.stdout).get("blockdevices", [])
    disks = []
    complex_devices = []

    def descendants(device):
        for child in device.get("children", []):
            yield child
            yield from descendants(child)

    all_devices = {}
    for device in block_devices:
        all_devices[device.get("name")] = device
        for child in descendants(device):
            all_devices.setdefault(child.get("name"), child)
    for device in all_devices.values():
        device_type = device.get("type", "")
        if device_type.startswith(("raid", "lvm", "crypt", "mpath")):
            complex_devices.append({
                "path": device.get("name"),
                "type": device_type,
                "size_bytes": device.get("size"),
                "filesystem": device.get("fstype"),
                "mountpoints": device.get("mountpoints") or [],
            })
        if device_type != "disk":
            continue
        disks.append({
            "path": device.get("name"),
            "model": (device.get("model") or "").strip() or None,
            "transport": device.get("tran"),
            "size_bytes": device.get("size"),
            "removable": bool(device.get("rm")),
            "read_only": bool(device.get("ro")),
            "partitions": [
                {
                    "path": part.get("name"),
                    "size_bytes": part.get("size"),
                    "filesystem": part.get("fstype"),
                    "label": part.get("label"),
                    "uuid": part.get("uuid"),
                    "parttype": part.get("parttype"),
                    "mountpoints": part.get("mountpoints") or [],
                }
                for part in descendants(device)
                if part.get("type") == "part"
            ],
        })
    vmd_devices = sys_root / "bus/pci/drivers/vmd"
    controller_ids = sorted(
        path.name for path in vmd_devices.iterdir()
        if path.name[:4].isdigit() and ":" in path.name
    ) if vmd_devices.is_dir() else []
    return {
        "read_only": True,
        "boot_mode": "UEFI" if (sys_root / "firmware/efi").is_dir() else "Legacy BIOS",
        "intel_vmd_module_loaded": (sys_root / "module/vmd").is_dir(),
        "intel_vmd_controllers": controller_ids,
        "disks": disks,
        "complex_devices": complex_devices,
        "os_probe": probe_installed_systems(),
    }


def format_size(size_bytes):
    value = float(size_bytes or 0)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024


def format_report(inventory):
    lines = [
        "ПРЕДВАРИТЕЛЬНАЯ ПРОВЕРКА (ТОЛЬКО ЧТЕНИЕ)",
        "Диски и разделы не изменяются.",
        f"Режим загрузки: {inventory['boot_mode']}",
        "Intel VMD: модуль загружен" if inventory["intel_vmd_module_loaded"] else "Intel VMD: модуль не загружен (это не доказывает отсутствие контроллера)",
    ]
    if inventory["intel_vmd_controllers"]:
        lines.append("VMD-контроллеры: " + ", ".join(inventory["intel_vmd_controllers"]))
    lines.append("")
    if not inventory["disks"]:
        lines.append("Накопители не обнаружены.")
    for disk in inventory["disks"]:
        description = " · ".join(filter(None, [disk["model"], disk["transport"]]))
        lines.append(f"{disk['path']} · {format_size(disk['size_bytes'])}" + (f" · {description}" if description else ""))
        for part in disk["partitions"]:
            details = " · ".join(filter(None, [part["filesystem"], part["label"], part["uuid"]]))
            line = f"  {part['path']} · {format_size(part['size_bytes'])}"
            if details:
                line += f" · {details}"
            if part["mountpoints"]:
                line += " · подключён: " + ", ".join(part["mountpoints"])
            lines.append(line)
    if inventory["complex_devices"]:
        lines.append("\nСоставные устройства (RAID/LVM/шифрование):")
        for device in inventory["complex_devices"]:
            lines.append(
                f"  {device['path']} · {device['type']} · {format_size(device['size_bytes'])}"
            )
    os_probe = inventory.get("os_probe", {"status": "unavailable", "systems": []})
    lines.append("\nУстановленные системы:")
    if os_probe["status"] == "not_implemented_safe_scan":
        lines.append("  Сканирование не выполнялось: безопасный ограниченный режим установщика ещё не реализован.")
    elif os_probe["status"] == "complete":
        for system in os_probe["systems"]:
            lines.append(
                f"  {system['partition']} · {system['name']} · {system['family']}"
            )
    elif os_probe["status"] == "none_found":
        lines.append("  ОС не обнаружены; это не доказывает, что их нет.")
    else:
        lines.append(f"  Не удалось выполнить сканирование: {os_probe['status']}.")
    lines.extend([
        "",
        "План установки пока не исполняется; preview требует безопасного обнаружения ОС.",
        "Не меняйте режим Intel RST/VMD в UEFI: сначала нужно подтвердить поддержку контроллера и массивов.",
    ])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only Localzet installer preflight")
    parser.add_argument("--plan-target", help="partition to include in a preview-only install plan")
    parser.add_argument("--plan-efi", help="existing EFI System Partition to preserve")
    parser.add_argument("--image", help="read-only inspect a regular disk image without mounting it")
    parser.add_argument(
        "--inspect-os",
        action="store_true",
        help="identify operating systems in --image using read-only libguestfs inspection",
    )
    parser.add_argument(
        "--include-format-in-preview",
        action="store_true",
        help="explicitly include formatting the selected target in the preview; performs no writes",
    )
    args = parser.parse_args(argv)
    try:
        if args.image:
            report = inspect_disk_image(args.image)
            if args.inspect_os:
                report["operating_systems"] = inspect_image_operating_systems(args.image)
                report["os_detection"] = report["operating_systems"]["status"]
                bind_operating_system_partitions(report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        if args.inspect_os:
            raise ValueError("--inspect-os requires --image")
        inventory = collect_inventory()
        if args.plan_target or args.plan_efi or args.include_format_in_preview:
            if not args.plan_target or not args.plan_efi:
                raise ValueError("A preview requires both --plan-target and --plan-efi")
            plan = build_install_plan(
                inventory,
                args.plan_target,
                args.plan_efi,
                confirm_format=args.include_format_in_preview,
            )
            print(json.dumps(plan, ensure_ascii=False, indent=2))
        else:
            print(format_report(inventory))
    except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError) as error:
        print(f"Не удалось безопасно прочитать сведения о дисках: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
