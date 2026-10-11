#!/usr/bin/env bash
# First Ubuntu pass: host diagnostics and Rust check; no sudo, no ISO build.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="$ROOT/out/first-build-$(date -u +%Y%m%d-%H%M%S)"
mkdir -p "$REPORT"
exec > >(tee "$REPORT/console.log") 2>&1
printf 'REPORT_DIR=%s\n' "$REPORT"
uname -a
. /etc/os-release
printf 'OS=%s\n' "$PRETTY_NAME"
df -h "$ROOT" /tmp
free -h
for cmd in cargo rustc pkg-config lb qemu-system-x86_64 xorriso git; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf '%s: %s\n' "$cmd" "$(command -v "$cmd")"
    case "$cmd" in cargo|rustc) "$cmd" --version;; esac
  else printf '%s: MISSING\n' "$cmd"; fi
done
bash "$ROOT/scripts/check-source-tree.sh"
source_result=$?
printf 'SOURCE_TREE_EXIT=%s\n' "$source_result"
python3 -m unittest discover -s "$ROOT/tests" -p 'test_*.py'
tests_result=$?
printf 'PYTHON_TEST_EXIT=%s\n' "$tests_result"
if command -v cargo >/dev/null 2>&1; then
  (cd "$ROOT" && CARGO_TARGET_DIR="$ROOT/out/cargo-target" cargo check --workspace --all-targets) 2>&1 | tee "$REPORT/cargo-check.log"
  rust_result=${PIPESTATUS[0]}
else
  rust_result=127
  echo 'cargo unavailable; Rust build skipped'
fi
printf 'CARGO_CHECK_EXIT=%s\n' "$rust_result"
(cd "$(dirname "$REPORT")" && tar -czf "$REPORT.tar.gz" "$(basename "$REPORT")")
printf 'SEND_THIS=%s.tar.gz\n' "$REPORT"
if (( source_result || tests_result || rust_result )); then exit 1; fi
