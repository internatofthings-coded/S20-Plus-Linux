# Hardware Support Matrix (SM-G985F / Exynos 990)

| Subsystem | Status | Notes |
|---|---|---|
| **CPU (8 cores + ACPM DVFS)** | **Verified** | All 8 cores operational under `schedutil` (`exynos990-cpufreq`). |
| **Internal UFS Storage** | **Verified** | Native Debian 13 ARM64 rootfs; boot persistence verified. |
| **Display (1440×3200 OLED)** | **Verified** | Bootloader-initialized `simple-framebuffer` (`fb0`); physical OLED sleep/wake via `boros_oled.ko` MIPI DCS. |
| **Touchscreen (`s6sy761`)** | **Verified** | Multitouch operational via S2DOS05 display sub-PMIC rails (`tsp_io` 1.8V, `tsp_avdd` 3.0V). |
| **On-Screen Keyboard** | **Verified** | `buffyboard` `3.5.1+dfsg-2` + `uinput.ko` on `tty1` (known logout redraw defect; see `KNOWN-LIMITATIONS.md`). |
| **Power Button** | **Verified** | Short press (`<3 s`) terminates local `tty1` sessions + toggles OLED; long press (`>=4 s`) triggers graceful `systemctl poweroff`. |
| **USB Gadget Networking** | **Verified** | USB ECM `usb0` + SSH/SCP/SFTP verified. |
| **Wi-Fi (BCM4375)** | **Partial** | Link reported; Wi-Fi SSH and transport qualification not established. Device-specific firmware required. |
| **USB serial console** | Local serial recovery; not independent of the running kernel/rootfs. |
| **Battery & Thermal Telemetry** | **Verified** | `max170xx_battery`, `max77705-charger`, and Exynos 990 ACPM TMU thermal zones (`boros-health.timer`). |
| **Hardware Thermal / Battery Cutoffs** | **Unverified** | Configured in DTS/drivers; live fault/overheat actuation intentionally not forced. |
| **GPU Acceleration (Mali-G77)** | **Unsupported** | Not enabled in this headless/console/TUI configuration. |
| **Audio, Cameras, Cellular Modem, Suspend-to-RAM** | **Unsupported** | Out of scope for v0.1.0. |
