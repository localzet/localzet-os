# Iteration 20: Source Gate Hardening

CI now rejects a missing Live ISO dependency before attempting Rust compilation.

Required chain: Rust workspace, systemd daemon, labwc session, desktop entries, guest serial marker, QEMU smoke test, ISO validator and release gate.

Local tests: 18 Python tests passed; Bash and static release checks passed. This is not a Rust compile result and does not prove ISO boot.

## Build steps

```bash
bash scripts/check-source-tree.sh
python3 -m unittest discover -s tests -p 'test_*.py'
bash scripts/verify-release.sh
bash scripts/build-localzet-live.sh
```

Only publish a bootable release after a successful Rust build, ISO generation, QEMU guest marker, and matching SHA256 report.
