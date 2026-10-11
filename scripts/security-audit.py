#!/usr/bin/env python3
"""Инвентаризация безопасности без изменения конфигурации Linux."""
import argparse
import json
from pathlib import Path
from shutil import which

def probe(identifier, executable=None, path=None):
    detected = Path(path).exists() if path else which(executable) is not None
    return {"id": identifier, "detected": detected, "evidence": "path:" + path if path else "command:" + executable}

def checks():
    return {"schema_version": 1, "assessment": "inventory_only", "certified": False, "checks": [
        probe("uefi", path="/sys/firmware/efi"),
        probe("tpm2", path="/dev/tpmrm0"),
        probe("apparmor", path="/sys/module/apparmor/parameters/enabled"),
        probe("selinux", path="/sys/fs/selinux"),
        probe("nftables", executable="nft"),
        probe("auditd", executable="auditctl"),
        probe("luks_tools", executable="cryptsetup"),
        probe("secureboot_tools", executable="mokutil"),
        probe("nvidia_tools", executable="nvidia-smi"),
    ]}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = checks()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["checks"]:
            print(("[НАЙДЕНО] " if item["detected"] else "[НЕТ] ") + item["id"])
        print("Инвентаризация не является сертификацией ФСТЭК/ФСБ.")
