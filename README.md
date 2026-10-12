# Localzet OS

[![CI](https://github.com/localzet/localzet-os/actions/workflows/ci.yml/badge.svg)](https://github.com/localzet/localzet-os/actions/workflows/ci.yml)
![Rust](https://img.shields.io/badge/Rust-основной_язык-orange)
![Стадия](https://img.shields.io/badge/стадия-экспериментальная-yellow)
![Лицензия](https://img.shields.io/badge/лицензия-MIT-blue)

**Localzet OS** — экспериментальный проект настольной операционной системы с собственными компонентами на Rust и совместимостью с экосистемой Linux.

> **Внимание:** это ранний прототип, а не готовый дистрибутив. BIOS Live ISO Alpha 3 локально загрузился в QEMU и запустил Wayland-сессию. UEFI, реальное оборудование и воспроизводимость новой сборки из GitHub пока не подтверждены.

## Цель

Создать полноценную замену Ubuntu, сохранив поддержку Linux-приложений, драйверов, Docker, сети и привычных инструментов разработки. Развивать собственную оболочку, системные службы и интеграцию устройств на Rust.

## Архитектура

```text
Localzet Panel / Launcher / Desktop (Rust + GTK4)
                    ↓
              labwc / Wayland
                    ↓
       Localzet Runtime / Linux userspace
                    ↓
             Debian Trixie / Linux
```

## Состояние

| Компонент | Статус |
|---|---|
| Исходники компонентов Rust | Экспериментальные |
| Панель и меню приложений | Alpha 3 запускалась; новый дизайн Surface требует проверки |
| Сборщик Live ISO | Локальный патченный legacy live-build; чистая сборка не подтверждена |
| Загрузка в QEMU | BIOS Alpha 3 подтверждена локально |
| NVIDIA и ноутбуки | Не проверены |

## Сборка

Работайте в **отдельной виртуальной машине Debian Trixie**, не на основном компьютере.

После добавления полного исходного дерева:

```bash
sudo apt update
sudo apt install live-build rsync sudo git python3 qemu-system-x86
./scripts/verify-release.sh
./scripts/build-localzet-live.sh
./scripts/qemu-graphical-smoke.sh out/localzet-live/localzet-os.iso out/qemu-smoke
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

## Alpha 3 и Localzet Surface

- [Проверенные исправления и ограничения Alpha 3](docs/ALPHA3-RECOVERY.md)
- Surface: верхняя панель с часами в центре, нижний плавающий Dock и кнопка меню. Стеклянные поверхности сейчас полупрозрачные, без гарантированного фонового размытия.
- Новые исходники ещё не проходили CI и тест загрузки ISO.

## Лицензия

Собственный код проекта — MIT. Компоненты Debian, Linux, GTK и других сторонних проектов сохраняют свои лицензии.
