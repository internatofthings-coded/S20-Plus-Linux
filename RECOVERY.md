# Recovery & Rollback Guide

## 1. Emergency Recovery Cheat Sheet

| Issue | Recovery Action |
|---|---|
| **Bypass TUI for one SSH login** | `ssh -t <user>@<device-ip> 'NAOMI_NO_TUI=1 exec $SHELL -l'` |
| **Disable TUI for current user** | `touch ~/.naomi-no-tui` |
| **Disable TUI system-wide** | `sudo touch /etc/boros/no-tui` (or set `AUTO_LAUNCH=0` in `/etc/boros/tui.conf`) |
| **Garbled terminal after crash** | `stty sane; printf '\033[?1049l\033[?25h\033[0m'` |
| **OLED stuck off** | Over USB SSH, stop `boros-powerkeyd` before any direct OLED sysfs write. See below. |
| **Buffyboard missing on `tty1`** | `sudo systemctl restart boros-buffyboard.service` |
| **Emergency hardware reboot** | Use the device-specific recovery procedure only as a last resort; forced reset may lose data. |

## OLED recovery

With a verified USB SSH or serial session, stop `boros-powerkeyd.service`, request OLED wake (`echo 1 | sudo tee /sys/kernel/boros_oled/power`), and check its status. Restore getty and Buffyboard if required. Restart the daemon only after the display and login state are consistent. Do not directly toggle sysfs with the daemon running.

## 2. Layer-by-Layer Rollback (No Kernel Reflash)

- **Bundle B (TUI + terminal hooks):** `sh scripts/rollback-bundle-b.sh`
- **Bundle A (MOTD + artwork):** `sh scripts/rollback-bundle-a.sh`
- **P04 Telemetry:** `systemctl disable --now boros-health.timer boros-health.service` and remove `/etc/systemd/system/boros-health.*` and `/usr/local/bin/boros-telemetry`.
- **P03 OLED & Powerkey:** Stop the daemon, wake the OLED and verify local login first. Then `systemctl disable --now boros-powerkeyd.service boros-oled.service`, remove unit files, `/usr/local/sbin/boros-powerkeyd.py`, `/etc/systemd/logind.conf.d/10-boros-powerkey.conf`, and `boros_oled.ko`; run `depmod -a && systemctl daemon-reload && systemctl restart systemd-logind`.
- **P02 Buffyboard & `uinput`:** `systemctl disable --now boros-buffyboard.service boros-uinput.service`, remove unit files, `/etc/udev/rules.d/99-boros-uinput.rules`, `/etc/buffyboard.conf`, and `uinput.ko`.

## 3. Kernel Rollback

Several kernel-specific services are guarded by `ConditionKernelVersion=6.12.119-g970959bbf675`. If a kernel fails to boot, use the previously validated device-specific recovery path and the known-good fallback image. The exact bootloader and flashing procedure are not reconstructed in this archive.
