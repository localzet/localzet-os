# Итерация 16 — графический smoke-test

## Что изменено

В локальном исходном архиве сборщик устанавливает `localzet-guest-boot-marker`. Скрипт вызывается из `labwc autostart` и записывает строку `LOCALZET_GUI_SESSION_READY_V1` в гостевую последовательную консоль, если существует `WAYLAND_DISPLAY`.

Хостовый `scripts/qemu-graphical-smoke.sh` собирает журнал QEMU, проверяет точное совпадение строки и записывает JSON-отчёт с SHA-256 ISO.

## Запуск после сборки

```bash
./scripts/build-localzet-live.sh
./scripts/qemu-graphical-smoke.sh out/localzet-live/live-image-amd64.hybrid.iso
./scripts/release-gate.sh out/localzet-live/live-image-amd64.hybrid.iso out/qemu-smoke/boot-report.json
```

**Важно:** маркер подтверждает достижение `labwc autostart`, но не работоспособность панели, отрисовку рабочего стола, безопасность загрузки или поддержку GPU. Это не криптографическая аттестация.

## Статус

Локально пройдено 11 Python-тестов; синтаксис Bash и целостность ZIP проверены. QEMU и Rust не запускались. Полное дерево исходников пока не синхронизировано с GitHub.
