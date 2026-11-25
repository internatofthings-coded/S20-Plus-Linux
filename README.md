# S20-Plus-Linux — NAOMI

An experimental native Linux port for the **Samsung Galaxy S20+ (SM-G985F, Exynos 990 / y2s)**, running **Debian 13 (trixie) ARM64** with a modified **Linux 6.12.119 LTS** kernel.

NAOMI is a personal project to repurpose an older smartphone as a small Linux server. It builds on Bentlybro's [Galaxy S20 Ultra Linux port](https://github.com/Bentlybro/z3s-mainline-linux), other upstream work, and AI-assisted engineering. The device boots native Linux rather than running Debian inside Android.

> **Experimental — no warranty.** This is a source snapshot of a working prototype, not a ready-to-flash distribution. The build and installation materials still require reconciliation. Flashing or changing partitions can erase data, render a device unusable or damage hardware. Battery and thermal protections are not fully qualified. Do not use it as an unattended always-on server or on a damaged battery. Use at your own risk, subject to applicable law. No affiliation with or endorsement by Samsung, Debian or the AI providers is implied.

## What works on the prototype

Tested on one SM-G985F running Boot-052 (`6.12.119-g970959bbf675`):

- Eight CPU cores and native Debian on internal UFS storage.
- Framebuffer console, touchscreen and Buffyboard on-screen keyboard.
- Physical OLED sleep/wake, local session termination on short Power press, and orderly shutdown on a four-second hold.
- Battery percentage, charging status, voltage/current, and temperature monitoring.
- Dynamic login MOTD and editable ANSI artwork.
- Native Ratatui interface with keyboard navigation and direct shell recovery.
- USB networking, serial console recovery, SSH, SCP and SFTP.
- Seven core services active after reboot, with zero failed systemd units at the final check.

Wi-Fi link operation was reported during development; Wi-Fi SSH and broader network qualification are not established here. GPU acceleration, audio, cameras, cellular service and suspend-to-RAM are not claimed. Only the SM-G985F was tested; do not assume compatibility with other S20 models.

## Repository contents

| Directory | Contents |
|---|---|
| `kernel/` | 15 patches, kernel configuration, device tree and OLED module source |
| `bootloader/` | Boot integration reference notes (incomplete) |
| `userspace/` | Systemd, keyboard, power control, telemetry, MOTD and terminal hooks |
| `artwork/` | Independently editable ANSI templates |
| `tui/` | Rust/Ratatui interface foundation and theme |
| `scripts/` | Installation, rollback and qualification utilities |

## Documentation

- [Release status and outstanding gates](RELEASE-STATUS.md) — read first.
- [Build notes](BUILD.md) · [Installation status](INSTALL.md) · [Recovery](RECOVERY.md)
- [Hardware support](HARDWARE-SUPPORT.md) · [Known limitations](KNOWN-LIMITATIONS.md)
- [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)
- [Licensing](LICENSE) · [Third-party notices](THIRD-PARTY-NOTICES.md) · [Acknowledgments](ACKNOWLEDGMENTS.md)

## Credits

 **Bentlybro** and the Exynos 990 Linux community for the foundational work that made this project possible.  Linux, Samsung's open-source contributors, Debian, postmarketOS/Buffyboard, Ratatui and Crossterm. Development was directed and physically test on my personal device.

See [Acknowledgments](ACKNOWLEDGMENTS.md) for the detailed credits and [Third-party notices](THIRD-PARTY-NOTICES.md) for source links and license information.
