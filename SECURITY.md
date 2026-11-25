# Security Policy

## Authentication Boundaries & Service Hardening

- **Local Console (`tty1`):** Standard `agetty` + PAM `login`. No auto-login; no `agetty --noclear`.
- **Unprivileged OSK (`boros-buffyboard.service`):** Runs as `buffyboard:buffyboard` with `NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `CapabilityBoundingSet=`, `DevicePolicy=closed`, and `MemoryMax=32M`. Access is restricted to `/dev/fb0`, `/dev/tty0`, `/dev/tty1`, `/dev/uinput` (`0660`), and `/dev/input/boros-touch` (`0660`). No broad `input` group is granted.
- **Fail-Closed Power-Button Lock (`boros-powerkeyd`):** Short press terminates all `tty1` sessions via `loginctl`, verifies termination, stops `boros-buffyboard.service`, and restarts or checks `getty@tty1.service` as needed before turning off the OLED. If session termination fails, OLED power-off is aborted.
- **SSH / SCP / SFTP:** Profile hooks (`99-boros-motd.sh`, `99-boros-tui.sh`) are strictly gated to interactive TTYs and emit 0 bytes in noninteractive shells. `AUTO_LAUNCH=0` is the default.

The TUI runs without root privileges; the on-screen keyboard has trusted pre-authentication input access. The above describes the intended configuration, not an independent security certification.

## RustSec Vulnerability Audit Status

- `tui/Cargo.toml` pins `ratatui = "=0.29.0"` (`default-features = false, features = ["crossterm"]`) and `crossterm = "=0.28.1"`.
- **RustSec Advisory Audit (`cargo audit`):** **PENDING** — actual deployed lockfile not included. The earlier dependency policy check passed, but is not a vulnerability scan. See [RustSec](https://rustsec.org/) and [release gates](RELEASE-STATUS.md).
- Run the following in a provisioned build environment after recovering the exact deployed `tui/Cargo.lock`:
  ```sh
  cargo install --locked cargo-audit
  cargo audit -f tui/Cargo.lock
  ```

## Reporting a Vulnerability

Use private vulnerability reporting if enabled, or contact without publicly posting exploit details, via <https://github.com/internatofthings-coded/S20-Plus-Linux>. Do not include device serial numbers, IMEI, EFS dumps, or private keys in reports.
