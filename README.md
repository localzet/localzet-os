# Localzet OS

[![CI](https://github.com/localzet/localzet-os/actions/workflows/ci.yml/badge.svg)](https://github.com/localzet/localzet-os/actions/workflows/ci.yml)
![Rust](https://img.shields.io/badge/Rust-основной_язык-orange)
![Стадия](https://img.shields.io/badge/стадия-экспериментальная-yellow)
![Лицензия](https://img.shields.io/badge/лицензия-MIT-blue)

**Localzet OS** — экспериментальный проект настольной операционной системы с собственными компонентами на Rust и совместимостью с экосистемой Linux.

> **Внимание:** это ранний прототип, а не готовый дистрибутив. Сборка ISO, загрузка в QEMU и работа на реальном оборудовании пока не подтверждены.

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
| Панель и меню приложений | Не проверены в реальном запуске |
| Сборщик Live ISO | Не проверен |
| Загрузка в QEMU | Не подтверждена |
| NVIDIA и ноутбуки | Не проверены |

## Сборка

Работайте в **отдельной виртуальной машине Debian Trixie**, не на основном компьютере.

После добавления полного исходного дерева:

```bash
sudo apt update
sudo apt install live-build rsync sudo git python3 qemu-system-x86
./scripts/verify-release.sh
./scripts/build-localzet-live.sh
./scripts/test-live-qemu.sh
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

Реальные скриншоты появятся после подтверждённого графического запуска. Макеты не выдаются за изображения работающей ОС.

## Лицензия

Собственный код проекта — MIT. Компоненты Debian, Linux, GTK и других сторонних проектов сохраняют свои лицензии.
