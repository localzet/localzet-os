#!/usr/bin/env bash
set -euo pipefail
MODE="${1:---build}"
errors=0
for command_name in bash git rsync sha256sum; do
  if ! command -v "$command_name" >/dev/null; then echo "MISSING: $command_name" >&2; errors=$((errors+1)); fi
done
if [[ "$MODE" == --build ]]; then
  for command_name in lb sudo; do
    if ! command -v "$command_name" >/dev/null; then echo "MISSING: $command_name" >&2; errors=$((errors+1)); fi
  done
  if [[ "$(uname -m)" != x86_64 ]]; then echo 'WARNING: amd64 ISO builds are tested only on x86_64 hosts' >&2; fi
  if [[ -r /etc/os-release ]]; then . /etc/os-release; echo "Host: ${PRETTY_NAME:-unknown}"; fi
  available_kb="$(df -Pk "${LOCALZET_BUILD_DIR:-.}" 2>/dev/null | awk 'NR==2 {print $4}' || true)"
  if [[ -z "$available_kb" ]]; then
    available_kb="$(df -Pk . | awk 'NR==2 {print $4}')"
  fi
  if [[ -n "$available_kb" && "$available_kb" -lt 20971520 ]]; then echo 'WARNING: less than 20 GiB free for Ubuntu GNOME image build' >&2; fi
fi
if ((errors)); then echo "$errors missing dependencies" >&2; exit 1; fi
echo 'Preflight passed (does not verify Rust compilation or ISO boot).'
