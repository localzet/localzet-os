#!/usr/bin/env python3
"""Read-only storage and firmware inventory for the future installer."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

EFI_SYSTEM_GUID = "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"


def probe_installed_systems(run=subprocess.run, effective_uid=None):
    if effective_uid is None:
        effective_uid = os.geteuid()
    if effective_uid != 0:
        return {"status": "requires_installer_privileges", "systems": []}
    try:
        result = run(
            ["os-prober"],
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
            env={"LC_ALL": "C", "PATH": "/usr/sbin:/usr/bin:/sbin:/bin"},
        )
    except FileNotFoundError:
        return {"status": "unavailable", "systems": []}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "systems": []}
    if result.returncode not in (0, 1) or (result.returncode == 1 and result.stderr.strip()):
        return {"status": "error", "systems": []}

    systems = []
    for line in result.stdout.splitlines():
        fields = line.split(":", 3)
        if len(fields) != 4 or not fields[0].startswith("/dev/"):
            continue
        systems.append({
            "partition": fields[0],
            "name": fields[1],
            "family": fields[2],
            "boot_method": fields[3],
        })
    return {"status": "complete" if systems else "none_found", "systems": systems}


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


def collect_inventory(run=subprocess.run, sys_root=Path("/sys"), effective_uid=None):
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
        "os_probe": probe_installed_systems(run, effective_uid),
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
    if os_probe["status"] == "requires_installer_privileges":
        lines.append("  Сканирование не запускалось: нужен привилегированный контекст установщика; текущий рабочий стол его не предоставляет.")
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
        "План установки пока не исполняется; preview доступен только отдельной командой и требует проверки ОС.",
        "Сканер ОС использует os-prober только из привилегированного контекста установщика.",
        "Не меняйте режим Intel RST/VMD в UEFI: сначала нужно подтвердить поддержку контроллера и массивов.",
    ])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only Localzet installer preflight")
    parser.add_argument("--plan-target", help="partition to include in a preview-only install plan")
    parser.add_argument("--plan-efi", help="existing EFI System Partition to preserve")
    parser.add_argument(
        "--include-format-in-preview",
        action="store_true",
        help="explicitly include formatting the selected target in the preview; performs no writes",
    )
    args = parser.parse_args(argv)
    try:
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
