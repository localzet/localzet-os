# Alpha 3: подтверждённая загрузка и исправления

Дата: 2026-10-12. На локальной машине пользователя проверена BIOS-загрузка Debian 13 Trixie Live ISO в QEMU с KVM, автоматический вход в labwc/Wayland и запуск Localzet Desktop. Это **не** означает подтверждения UEFI, реального оборудования, NVIDIA или воспроизводимой CI-сборки.

## Причина проблемы Alpha 2

В `/lib/live/init-config.sh` значение по умолчанию `LIVE_USERNAME=user`. В образе уже создан `localzet` с UID 1000. В Alpha 2 отсутствовал `username=localzet` в параметрах загрузчика. Поэтому добавлен явный параметр `username=localzet` к загрузке Live.

`/lib/live/config/0030-user-setup` пропускает создание пользователя, если он уже существует. `/lib/live/config/0100-lightdm` меняет только закомментированные строки основного `lightdm.conf`; отдельный конфиг в `lightdm.conf.d` имеет приоритет.

## Исправления

1. В параметрах ISO: `boot=live config components username=localzet` (без дублирования `boot=live`).
2. `/etc/lightdm/lightdm.conf.d/60-localzet.conf`: `autologin-user=localzet`, `autologin-session=localzet`, `user-session=localzet`, `session-wrapper=/usr/local/bin/localzet-lightdm-session`.
3. Wayland-wrapper: `#!/bin/sh; exec "$@"` вместо `/etc/X11/Xsession`.
4. Группа `autologin`, член `localzet`.
5. В тестовой Alpha 3 вручную был установлен временный пароль. **Не переносить его в публичные образы.** Сборочный скрипт блокирует пароль, а работу автологина с заблокированным паролем требуется повторно проверить.

## Особенности локальной сборки

На машине использовался патченный legacy live-build 3.0~a57, а дерево ISO находилось в `chroot/binary`, не в корневом `binary`. Эти особенности относятся к локальному аварийному процессу, а не к гарантированному стандартному `lb build`.

Сжатие: `mksquashfs -comp xz -b 131072`. Из SquashFS исключались `binary/**`, `opt/localzet-os/target/**`, временные cargo-кэши, `proc/**`, `sys/**`, `dev/**`, `run/**`, `mnt/**`, `media/**`, промежуточные ISO. Образ генерировался `genisoimage` внутри chroot и `isohybrid` с хоста. **Нельзя** включать в SquashFS каталог `chroot/binary` или промежуточный ISO.

## Запуск локальной Alpha 3

```bash
qemu-system-x86_64 -enable-kvm -cpu host -m 4096 -smp 4 \
  -cdrom /mnt/Data/localzet-os-build/releases/localzet-os-alpha3-bios.iso \
  -boot d -display gtk
```

## Дизайн Localzet Surface

Первая итерация: верхняя панель с центрированными часами, отдельный нижний плавающий Dock, кнопка запуска приложений. GTK4 layer-shell поддерживает полупрозрачность; настоящее размытие фона потребует поддержки Wayland-композитором. Текущие кнопки Dock статические, полноценный task switcher и центр управления ещё не реализованы.
