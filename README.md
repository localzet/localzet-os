# Localzet OS

[![CI](https://github.com/localzet/localzet-os/actions/workflows/ci.yml/badge.svg)](https://github.com/localzet/localzet-os/actions/workflows/ci.yml)
![Rust](https://img.shields.io/badge/Rust-основной_язык-orange)
![Стадия](https://img.shields.io/badge/стадия-экспериментальная-yellow)
![Лицензия](https://img.shields.io/badge/лицензия-MIT-blue)

**Localzet OS** — экспериментальная Ubuntu 26.04 LTS система с GNOME и собственными настольными компонентами на Rust.

> **Внимание:** это ранний прототип, а не готовый дистрибутив. Предыдущий Alpha 5 ISO был Debian/Labwc и не содержал установщика. Текущая ветка переводит образ на Ubuntu 26.04 и GNOME; свежая сборка должна пройти QEMU-проверку до публикации и записи на USB.

## Цель

Сохранить совместимость Ubuntu с Linux-приложениями, драйверами, пакетами APT и обновлениями, добавляя собственные приложения, интеграцию и системные службы Localzet.

## Архитектура

```text
       Localzet Launcher / Desktop (Rust + GTK4)
                    ↓
       GNOME Shell / Mutter / Wayland
                    ↓
       Localzet Runtime / Ubuntu userspace
                    ↓
             Ubuntu 26.04 / Linux
```

## Состояние

| Компонент | Статус |
|---|---|
| Исходники компонентов Rust | Экспериментальные |
| База системы | Ubuntu 26.04 LTS (`resolute`) |
| Рабочая среда | GNOME Shell 50, Yaru Magenta Dark, Ubuntu Dock; локальный GNOME launcher |
| Обновления | APT, GNOME Software, Update Manager и Snap backend из Ubuntu |
| Установщик | Не реализован в собственном образе; не устанавливайте его на диск |
| QEMU | Проверка новой GNOME-сборки ожидает локальную сборку и запуск |
| NVIDIA и реальное оборудование | Требуют отдельной проверки |

## Сборка

Для сборки используйте Ubuntu 26.04 x86_64 или GitHub Actions с образом `ubuntu-26.04`. Сборщик создаёт новое дерево в `out/localzet-ubuntu-26.04` и не трогает диски с установленными системами.

После добавления полного исходного дерева:

```bash
sudo apt update
sudo apt install live-build debootstrap squashfs-tools xorriso rsync git sudo python3 qemu-system-x86
./scripts/verify-release.sh
./scripts/build-localzet-live.sh
iso=$(find out/localzet-ubuntu-26.04 -maxdepth 1 -name '*.iso' -print -quit)
./scripts/validate-iso.sh "$iso"
./scripts/qemu-graphical-smoke.sh "$iso" out/qemu-smoke
./scripts/release-gate.sh "$iso" out/qemu-smoke/boot-report.json
```

Не записывайте экспериментальные образы на диск без проверки устройства и загрузки в виртуальной машине.

## Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [Сборка](docs/BUILD.md)
- [План развития](docs/ROADMAP.md)
- [Порядок релизов](docs/RELEASING.md)
- [Участие в разработке](CONTRIBUTING.md)
- [Безопасность](SECURITY.md)
- [Скриншоты](docs/screenshots/README.md)

Реальные скриншоты нового оформления появятся после его запуска и проверки. Макеты не выдаются за изображения работающей ОС.

## Предыдущий Alpha 5

- [Проверенные исправления и ограничения старого Debian/Labwc образа](docs/ALPHA3-RECOVERY.md)
- Новый образ использует GNOME Shell, а не отдельный композитор Localzet.
- GNOME launcher и настройки темы не заменяют собой полноценный установщик или проверку оборудования.

## Лицензия

Собственный код проекта — MIT. Компоненты Debian, Linux, GTK и других сторонних проектов сохраняют свои лицензии.
