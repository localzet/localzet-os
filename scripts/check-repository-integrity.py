#!/usr/bin/env python3
"""Check required project structure and basic accidental private-key leaks."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REQUIRED = (
    "Cargo.toml", "README.md", "LICENSE", "scripts/build-localzet-live.sh",
    "scripts/release-gate.sh", "packaging/systemd/localzetd.service",
    "packaging/session/localzet-session", "packaging/session/labwc/autostart",
)
CRATES = ("localzet-core", "localzetd", "localzetctl", "localzet-desktop", "localzet-panel", "localzet-launcher")
issues = []
for path in REQUIRED:
    if not (ROOT / path).is_file():
        issues.append(f"missing: {path}")
for crate in CRATES:
    folder = ROOT / "crates" / crate
    if not (folder / "Cargo.toml").is_file():
        issues.append(f"missing: {crate}/Cargo.toml")
    if not (folder / "src").is_dir() or not list((folder / "src").glob("*.rs")):
        issues.append(f"missing Rust sources: {crate}")
for path in ROOT.rglob("*"):
    if not path.is_file() or any(p in {".git", "target", "out", "__pycache__"} for p in path.parts):
        continue
    if path.suffix in {".pem", ".key", ".p12", ".pfx"}:
        issues.append(f"potential private key file: {path.relative_to(ROOT)}")
if issues:
    for issue in issues:
        print("FAIL:", issue, file=sys.stderr)
    sys.exit(1)
print("PASS: basic source integrity checks (not a full secrets scan)")
