# Сборка и проверка

Рабочая среда: Ubuntu 26.04 x86_64 с доступом к Ubuntu archive и не менее 20 GiB свободного места. Для QEMU нужно выделить гостю 8 GiB RAM.

```bash
sudo apt update
sudo apt install live-build debootstrap squashfs-tools xorriso rsync git sudo python3 qemu-system-x86
./scripts/check-source-tree.sh
./scripts/verify-release.sh
./scripts/build-localzet-live.sh
iso=$(find out/localzet-ubuntu-26.04 -maxdepth 1 -type f -name '*.iso' -print -quit)
./scripts/validate-iso.sh "$iso"
./scripts/qemu-graphical-smoke.sh "$iso" out/qemu-smoke
./scripts/release-gate.sh "$iso" out/qemu-smoke/boot-report.json
```

Команды будут доступны после публикации полного дерева исходников. Проверяйте каждый этап отдельно.

Live ISO строится `live-build` в режиме Ubuntu для `resolute`; графическая сессия — GNOME Shell под Wayland. `casper` создаёт временного пользователя `localzet` при загрузке. Это не устанавливаемая система: собственный установщик и безопасный план разметки диска пока отсутствуют.

**Критерии успешной сборки:** нулевой код завершения сборки, единственный непустой ISO, валидная контрольная сумма, запуск GNOME Wayland в QEMU и сохранённый снимок экрана.

Ни один из этих критериев пока не подтверждён на опубликованном релизе.

Rust-зависимости фиксируются в `Cargo.lock`; сборка ISO и CI используют `--locked`. Обновляйте их отдельным изменением lock-файла и проверяйте весь workspace.
