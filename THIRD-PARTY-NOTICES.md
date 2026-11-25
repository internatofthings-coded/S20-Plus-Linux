# Third-party notices and source provenance

This file records upstream material, build dependencies and reference sources. See [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) for personal and AI-assisted development credits. Attribution does not replace the applicable license obligations.

| Component | Source / version | Role and license notes |
|---|---|---|
| Bentlybro — z3s-mainline-linux | [Repository](https://github.com/Bentlybro/z3s-mainline-linux); exact reference commit pending | Foundational S20 Ultra Exynos 990 reference. Preserve upstream file licenses and copyright notices. |
| Linux | [Stable kernel tree](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git), v6.12.119; [kernel licensing rules](https://docs.kernel.org/process/license-rules.html) | GPL-2.0-only kernel as a whole; individual files may have other or dual license expressions. |
| Exynos990 Mainline | [Organization](https://github.com/exynos990-mainline); exact repository and commit pending | SoC reference material. Verify original licenses file by file. |
| Samsung SM-G985F source | [Samsung Open Source Release Center](https://opensource.samsung.com/), G985FXXSGHWD4 | Hardware and register references for the port. Verify notices and license for any copied code; vendor archive not included. |
| uniLoader | [Previously recorded reference](https://github.com/SoMainline/uniLoader) (not independently verified) | Exact fork, revision, modifications and license pending. No bootloader source is included here. |
| Buffyboard / Buffybox | [Upstream](https://gitlab.postmarketos.org/postmarketOS/buffybox); [Debian source tracking](https://tracker.debian.org/pkg/buffybox); [Debian package](https://packages.debian.org/sid/buffyboard), 3.5.1+dfsg-2 | On-screen keyboard, built from Debian sid source against Debian 13 dependencies. Not vendored; check package copyright and upstream license before redistribution. |
| Debian 13 ARM64 | [Debian](https://www.debian.org/), trixie | Base OS; individual packages have their own licenses. Not bundled. |
| Ratatui | [Upstream](https://github.com/ratatui/ratatui), [0.29.0](https://docs.rs/crate/ratatui/0.29.0) | Terminal UI framework; MIT (as recorded in the original audit). External Rust dependency. |
| Crossterm | [Upstream](https://github.com/crossterm-rs/crossterm), [0.28.1](https://docs.rs/crate/crossterm/0.28.1) | Terminal backend; MIT (as recorded in the original audit). External Rust dependency. |
| Rust transitive dependencies | [crates.io](https://crates.io/) | Exact deployed Cargo.lock and per-crate license inventory are pending inclusion. Do not treat all dependencies as MIT. |
| Google Gemini / Antigravity | [Gemini](https://gemini.google.com/), [Antigravity](https://antigravity.google/) | AI-assisted engineering; not a bundled software dependency. |
| OpenAI ChatGPT | [ChatGPT](https://chatgpt.com/) | AI-assisted planning, debugging and review; not a bundled software dependency. |

## Source-level notices

The kernel patch series contains existing copyright notices for Igor Belwon, Dzmitry Sankouski, Samsung Electronics, Google LLC and Linaro Ltd. Preserve these and any other upstream notices, including author and sign-off history when recovering the original commits.

The patches contain GPL-2.0 / GPL-2.0-only, ISC and dual GPL-2.0-only OR BSD-2-Clause identifiers. In particular, the Exynos990 clock binding header carries a dual license, and the S2MPU Wi-Fi wrapper source/header carry ISC identifiers. Do not replace these with a blanket GPL or MIT header. The included GPL text does not by itself establish compliance for all files; recover the applicable upstream notices and license texts before publication.

## Remaining provenance work

The source archive does not establish exact upstream commits for all adapted components, the complete modified bootloader and initramfs source, or a full dependency-license inventory. Recover these from the original working tree, confirm authorship/redistribution rights, and attach the actual lockfile. Do not infer missing author names or license terms. See [RELEASE-STATUS.md](RELEASE-STATUS.md).

## Firmware

No proprietary firmware binaries are included in this archive. Obtain any required device-specific firmware or calibration data lawfully, subject to the applicable terms. Never publish EFS, IMEI, calibration dumps or private device identifiers.
