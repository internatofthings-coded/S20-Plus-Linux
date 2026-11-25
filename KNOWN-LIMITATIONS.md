# Known Limitations & Unverified Protections

This document records all known defects, deferred tests, and unverified hardware safety protections as of **v0.1.0**.

1. **Buffyboard Logout Redraw Defect:** Logging out of `tty1` causes `agetty` to clear `/dev/fb0`, hiding the Buffyboard on-screen keyboard until redraw/restart; touching may repaint only individual keys, and power-button wake can restore the keyboard. A proposed P09 `getty@tty1.service` drop-in fix was **not** approved for deployment and is excluded from this release.
2. **Extended 20-Cycle OLED Qualification Waived:** Single physical OLED off/on and normal interactive lock/wake cycles are verified, but extended 20-cycle endurance qualification was waived.
3. **OLED Power-Saving Measurements Incomplete:** Quantitative battery current delta (OLED ON vs. OLED OFF) has not yet been completed across a full discharge baseline. Use `scripts/measure-resources-power.sh` for passive observation.
4. **Long-Term Continuous 24/7 Charging Suitability Unverified:** Holding a Li-ion pouch cell continuously at `4.38 V` (100% SoC) accelerates calendar aging and swelling risk; multi-day soak testing has not been performed.
5. **Charger I2C Watchdog Limitation:** The `max77705` charger I2C watchdog (`WDTEN`) is disabled in the current kernel driver. If Linux hangs mid-charge, software thermistor polling (`5 s`) stops (hardware silicon die thermal regulation, `4.38 V` CV, and `10h` `FCHGTIME` are configured or expected from source; their physical enforcement is unverified).
6. **Physical Thermal & Battery Safety Actuation Unverified:** CPU/SoC thermal throttling (`>= 75 °C`), critical thermal shutdown (`105 °C` kernel / `115 °C` APM), and battery overcharge/over-temp/undervoltage cutoffs are configured or described in DTS and driver source; physical enforcement is unverified. Live fault injection and artificial overheating are intentionally **not** performed.
7. **Cold-Boot Touchscreen First-Read Quirk:** Immediately after a cold boot, the very first touch probe once recorded 0 events before subsequent testing worked; the cause of the initial failure was not established.
8. **Framebuffer-Only Display:** `FBIOBLANK` is unsupported on `simple-framebuffer`; physical OLED blanking relies on `boros_oled.ko`.

9. **Release reproduction gaps:** See [RELEASE-STATUS.md](RELEASE-STATUS.md) for missing bootloader, initramfs, touchscreen service and lockfile.
10. **Local lock semantics:** Power-button locking terminates the local terminal session; it does not preserve running local applications. OLED sleep does not suspend the server.
11. **Unattended use:** Do not use this prototype as an unattended continuously charging server until battery and thermal safety are addressed. Stop use if battery swelling, abnormal heat or damage is observed.
