#!/usr/bin/env bash
# Static source validation; this does NOT validate a booted ISO.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "$ROOT/scripts/check-source-tree.sh"
for script in "$ROOT"/scripts/*.sh; do bash -n "$script"; done
python3 - "$ROOT" <<'PY'
from pathlib import Path
import sys, tomllib, xml.etree.ElementTree as ET
root = Path(sys.argv[1])
members = tomllib.loads((root / "Cargo.toml").read_text())["workspace"]["members"]
for member in members:
    assert (root / member / "Cargo.toml").is_file()
ET.parse(root / "packaging/session/labwc/rc.xml")
build = (root / "scripts/build-localzet-live.sh").read_text()
assert "sudo lb build" in build
assert "passwd -l localzet" in build
assert "NOPASSWD:ALL" not in build
print("PASS: static release wiring only")
PY
