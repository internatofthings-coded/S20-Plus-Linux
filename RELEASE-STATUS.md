# Release status — v0.1.0 draft

**Experimental source snapshot; not yet a reproducible installation release.** The maintainer has a working prototype, but this archive is incomplete for a fresh device. Keep the GitHub repository private until the release gates below are resolved.

| Gate | Status / action |
|---|---|
| Actual TUI lockfile | Missing. Copy the exact lockfile from the successfully built Debian ARM64 container workspace, not a newly generated lockfile. Its recorded SHA-256 is `261f16ca9f160049931f162101f0f858e0e9bbac2e8a1063a59ae3e6d0d0db93`. |
| Vulnerability and dependency licenses | Dependency policy check passed on the build host, but RustSec and full dependency-license checks are pending. Kernel/OS security review is also not complete. |
| Upstream provenance | Confirm exact repositories, revisions, patch ancestry and original notices for all adapted code. In particular, confirm uniLoader fork, source and modifications. |
| License approval | MIT for original userspace/TUI/artwork/documentation remains proposed; obtain maintainer approval and verify the right to license each component. Preserve per-file upstream licenses. |
| Boot chain | Modified uniLoader source/patches, initramfs build recipe and actual boot packaging parameters are missing. Recover and validate these before providing flash instructions. |
| Touchscreen startup | `boros-touch.service` is required by the published userspace units and qualification script but missing from the archive. Recover it and its installation procedure. |
| Kernel identity | Exact Boot-052 kernel release is hardcoded in unit conditions. Rebuilt commit hashes may differ; document an ABI-checked installation procedure. Confirm the patch series reproduces the deployed source/config. |
| OLED service | Included source unit contains `DefaultDependencies=no`, unlike the unit installed during qualification. Reconcile with deployed configuration before claiming an exact snapshot. |
| Build and install | No clean-room reconstruction or independent fresh-device installation has been performed. Current recipes are reference notes, not a validated installer. |
| Hardware safety | Unverified long-term charging, charger watchdog and thermal/battery actuation remain open. Do not advertise unattended 24/7 use as safe. |
| Privacy and publication | Automated text scan is not a guarantee; review all source and attribution before approval. Publish repository files only, not private review reports. |

No flashable images or binaries are provided. Do not treat the release as an official Samsung, Debian, Google or OpenAI product. See [KNOWN-LIMITATIONS.md](KNOWN-LIMITATIONS.md) for prototype limitations.
