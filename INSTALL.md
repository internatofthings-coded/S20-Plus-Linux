# Installation status — not ready for fresh-device installation

> **Warning:** Experimental software, no warranty. Unlocking or flashing a phone can erase data, break device functionality or cause hardware damage. The prototype's battery and thermal protections are not fully qualified. Use at your own risk, to the extent permitted by applicable law.

The tested target is **Samsung Galaxy S20+ SM-G985F (Exynos 990, y2s)** with native Debian 13 ARM64 on internal UFS. No fresh-device installation from this archive has been validated. microSD boot, other device variants and alternative flashing methods are not qualified.

Before publishing or following a complete installation guide, recover the exact tested bootloader and initramfs source, boot packaging recipe, root filesystem handoff and partition-selection procedure, and touchscreen startup service. Verify the module ABI, udev permissions, user/group setup, USB serial and USB networking recovery, and correct firmware handling. See [RELEASE-STATUS.md](RELEASE-STATUS.md) and [BUILD.md](BUILD.md).

The included Bundle A and Bundle B scripts are historical userspace installation utilities, not a complete OS installer. Bundle A changes the hostname to `naomi` and replaces the `127.0.1.1` hosts entry; back up `/etc/hostname` and `/etc/hosts` and preserve aliases before use. Bundle B can install hooks without a binary; require a verified binary first. Review exact destination paths and existing configurations before executing either as root. Do not enable automatic TUI launch until interactive shell recovery has been tested.

Do not flash an image or format a partition based on this draft. Do not modify S-Boot, PIT, EFS, modem or other unrelated partitions. No proprietary firmware is provided.
