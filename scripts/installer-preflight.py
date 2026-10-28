#!/usr/bin/env python3
"""Read-only storage and firmware inventory for the future installer."""
import json
from pathlib import Path
import subprocess
import sys


def collect_inventory(run=subprocess.run, sys_root=Path("/sys")):
    result = run(
        [
            "lsblk", "--json", "--bytes", "--paths", "--output",
            "NAME,TYPE,SIZE,MODEL,TRAN,RM,RO,FSTYPE,LABEL,UUID,MOUNTPOINTS,PKNAME",
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
    lines.extend([
        "",
        "Распознавание установленных ОС и планирование разметки ещё не выполняются.",
        "Не меняйте режим Intel RST/VMD в UEFI: сначала нужно подтвердить поддержку контроллера и массивов.",
    ])
    return "\n".join(lines)


def main():
    try:
        print(format_report(collect_inventory()))
    except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError) as error:
        print(f"Не удалось безопасно прочитать сведения о дисках: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
