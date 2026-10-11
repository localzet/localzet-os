# Localzet Desktop Alpha M2 — QEMU boot observer

Milestone M2 replaces the fixed-duration QEMU observation with a guest-marker-aware observer in the local source archive.

- Watch for a **complete serial line** `LOCALZET_GUI_SESSION_READY_V2`.
- Stop QEMU after marker detection, or after timeout/early exit.
- Save `serial.log` and `boot-report.json` with ISO SHA-256, elapsed seconds, process exit code, and explicit boolean result.
- Fail closed if the marker is absent.

Local checks: 23 Python unit tests, Bash syntax and ZIP integrity passed. **No ISO was built or booted here.** A process-presence marker does not prove successful rendering.

## Run on a Debian/Ubuntu workstation

```bash
sudo apt-get install -y live-build rsync qemu-system-x86 python3 xorriso
bash scripts/check-source-tree.sh
python3 -m unittest discover -s tests -p 'test_*.py'
bash scripts/build-localzet-live.sh
bash scripts/qemu-graphical-smoke.sh out/localzet-live/live-image-amd64.hybrid.iso
bash scripts/release-gate.sh out/localzet-live/live-image-amd64.hybrid.iso out/qemu-smoke/boot-report.json
```

The updated observer implementation is packaged in `localzet-os-desktop-alpha-m2.zip`; the GitHub copy of the script still needs synchronization. Do not interpret this document as evidence of successful QEMU execution.
