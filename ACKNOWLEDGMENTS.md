# Acknowledgments

S20-Plus-Linux (NAOMI) would not exist without the work already done by the Linux and mobile Linux communities. This project adapts existing work to the Galaxy S20+ SM-G985F; it is not a Linux port built from scratch.

## Special thanks

- **[Bentlybro](https://github.com/Bentlybro)** — [z3s-mainline-linux](https://github.com/Bentlybro/z3s-mainline-linux), the Galaxy S20 Ultra Exynos 990 port that provided the foundational reference for this S20+ effort, particularly SoC bring-up, storage, power management, Wi-Fi and touch support. Thank you for making your work available to others.
- **[Exynos990 Mainline contributors](https://github.com/exynos990-mainline)** — Exynos 990 SoC enablement and driver foundations.
- **Linux kernel contributors**, including **Igor Belwon**, **Dzmitry Sankouski**, and contributors at **Samsung Electronics**, **Google** and **Linaro**, whose copyright notices appear in the included patch series. Their original notices remain in the source. See [Linux](https://www.kernel.org/) and [Linaro](https://www.linaro.org/).
- **[Samsung Open Source Release Center](https://opensource.samsung.com/)** — SM-G985F source release G985FXXSGHWD4, consulted for vendor hardware definitions.
- **uniLoader and the mobile Linux community** — boot integration. The exact fork, commit and local changes still need to be recovered; see [bootloader notes](bootloader/README.md).
- **[postmarketOS](https://postmarketos.org/)** and **[Buffybox/Buffyboard contributors](https://gitlab.postmarketos.org/postmarketOS/buffybox)** — framebuffer on-screen keyboard.
- **[Debian](https://www.debian.org/)** and its package maintainers — Debian 13 ARM64 and the [Buffybox source package](https://tracker.debian.org/pkg/buffybox).
- **[Ratatui](https://ratatui.rs/)** and **[Crossterm](https://docs.rs/crate/crossterm/0.28.1)** contributors — the interactive terminal foundation.

## AI-assisted engineering

- **[Google Gemini](https://gemini.google.com/)** and **[Google Antigravity](https://antigravity.google/)** — implementation, code analysis, builds, debugging, test development and documentation.
- **[OpenAI ChatGPT](https://chatgpt.com/)** — architectural planning, research assistance, implementation review, troubleshooting, qualification guidance and documentation review.

I directed the development,research, made scope, safety decisions, and did physical device tests. AI tools assisted the work; their involvement does not imply endorsement, independent certification or affiliation with the providers.

## Supporting tools

Thanks to the communities behind [GCC](https://gcc.gnu.org/), [GNU Binutils](https://www.gnu.org/software/binutils/), [Rust](https://www.rust-lang.org/), [Cargo](https://doc.rust-lang.org/cargo/), [Python](https://www.python.org/), [systemd](https://systemd.io/), [OpenSSH](https://www.openssh.com/), [Podman](https://podman.io/), [QEMU](https://www.qemu.org/), [Fedora](https://fedoraproject.org/), [Git](https://git-scm.com/) and [RustSec](https://rustsec.org/). Build and verification tools are not necessarily shipped in this repository.

For component licenses, source links and unresolved provenance, see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). This credit list records the sources currently identified; it is not a claim that every historical reference or transitive dependency has been recovered. Corrections and additional credits are welcome.
