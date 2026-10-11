#!/usr/bin/env bash
# Предварительная инвентаризация: не меняет конфигурацию хоста.
set -euo pipefail
printf 'Localzet OS — предварительная диагностика безопасности\n'
check() {
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf '[OK] %s\n' "$label"
  else
    printf '[INFO] %s: не подтверждено\n' "$label"
  fi
}
check 'UEFI' test -d /sys/firmware/efi
check 'TPM' test -e /dev/tpmrm0
check 'AppArmor' test -e /sys/module/apparmor/parameters/enabled
check 'SELinux' test -d /sys/fs/selinux
check 'nftables' command -v nft
check 'auditctl' command -v auditctl
check 'LUKS' command -v cryptsetup
check 'Secure Boot tools' command -v mokutil
check 'NVIDIA' command -v nvidia-smi
printf 'Инвентаризация не является сертификацией ФСТЭК/ФСБ.\n'
