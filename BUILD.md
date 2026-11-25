# Build notes — incomplete draft

The working prototype used a Linux 6.12.119 ARM64 kernel and a Debian 13 ARM64 userspace. This archive has not been independently rebuilt from scratch. See [RELEASE-STATUS.md](RELEASE-STATUS.md) before attempting a build or installation.

## Kernel

The `kernel/` directory contains a 15-patch series, Boot-052 configuration, DTS and OLED module source. The intended base is [Linux stable v6.12.119](https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git). An ARM64 GCC cross-toolchain, binutils, make, bc, bison, flex, OpenSSL headers and device tree compiler are needed. Confirm the patch ancestry and apply in filename order in a disposable build tree; do not assume the patch series alone reproduces Boot-052. Build the kernel and modules from the matching configuration and verify the exact kernel release and module ABI. The `CONFIG_LOCALVERSION_AUTO` setting and hardcoded service kernel guards must be reconciled for a fresh build. Do not bypass a kernel guard just to load an incompatible module.

The OLED module must be built against the exact running kernel build tree. See `kernel/drivers/boros-oled/Makefile` for its build variables. The device tree snapshot is not a validated standalone boot recipe.

## Bootloader and initramfs

See [bootloader notes](bootloader/README.md). Exact local bootloader modifications, initramfs source and packaging parameters are missing. Do not generate a flashable image from guessed parameters.

## On-screen keyboard

The tested Buffyboard 3.5.1+dfsg-2 package was built from Debian sid source using trixie dependencies in an isolated ARM64 container. The historical builder is in `userspace/buffyboard/build-buffyboard-trixie.sh`. Pin and verify the source version; the script currently follows the available sid source rather than pinning it. Do not enable sid binary repositories on the target device.

## Ratatui interface

The maintainer successfully built the original TUI source and ran its unit tests inside a rootless Debian 13 ARM64 Podman container under QEMU emulation on a Linux host. Rust and Cargo were installed in that container, not on the device. The release binary was approximately 579 KiB. `tui/build-and-verify.sh` describes a separate cross-compilation route which was not the route used for the qualified build.

Recover the original deployed `tui/Cargo.lock` (see [release status](RELEASE-STATUS.md)); do not regenerate it as a substitute. From an appropriately provisioned Debian 13 ARM64 build environment, run the tests and release build with `cargo test --locked` and `cargo build --release --locked`. Record the actual toolchain, lockfile and binary hashes. Run `cargo audit -f tui/Cargo.lock` from the repository root with cargo-audit installed and an up-to-date advisory database. Review licenses and any findings separately.
