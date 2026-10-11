# Localzet Desktop Alpha: first boot

This is a **source preview**, not a tested ISO. On a Debian/Ubuntu x86_64 host:

```bash
sudo apt-get update
sudo apt-get install -y live-build rsync qemu-system-x86 python3 xorriso git
bash scripts/alpha-build-and-test.sh
```

The script runs source checks, builds the ISO, validates its filesystem, boots QEMU and requires a guest V2 readiness marker. On failure, inspect `out/qemu-smoke/serial.log` and `out/qemu-smoke/boot-report.json`. Process evidence does not prove successful visual rendering.

The guest user belongs to `dialout` for writing the QEMU serial marker. The ISO kernel boot arguments enable serial console output. Revisit these test settings before a production release.
