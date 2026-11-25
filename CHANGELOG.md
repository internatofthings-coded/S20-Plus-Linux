# Changelog

## [0.1.0] — Draft (2026-11-25)

### Added
- Linux **6.12.119 LTS** patch series (`0001`–`0015`), Boot-052 `.config`, and `exynos990-y2s-052.dts` for Samsung Galaxy S20+ (`SM-G985F`, Exynos 990).
- Out-of-tree `boros_oled.ko` MIPI DCS OLED power-off/on kernel module (`GPL-2.0-only`).
- `boros-powerkeyd` short-press `tty1` lock/OLED toggle and `>=4.0 s` graceful `systemctl poweroff`.
- `buffyboard` `3.5.1+dfsg-2` + `uinput` systemd units and least-privilege udev rules.
- `boros-telemetry` + `boros-health.timer` (60 s) battery and Exynos 990 ACPM TMU thermal monitoring.
- Dynamic MOTD (`boros-motd`, `boros_sysinfo`) and editable NAOMI ANSI Ouroboros artwork.
- Native Rust/Ratatui `naomi-tui` foundation (`tui/`) and safe terminal integration (`naomi-tui-launch`, `99-boros-tui.sh`).
- Live qualification, host SSH/SCP/SFTP verification, passive power/resource measurement, and `Cargo.lock` audit scripts.
