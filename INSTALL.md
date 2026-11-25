# Installation Guide

## 1. Requirements

- Samsung Galaxy S20+ SM-G985F (Exynos 990).
- Linux computer.
- USB data cable.
- Samsung stock firmware for recovery.
- Compatible UniLoader/LK3rd and NAOMI boot images.

**Warning:** Bootloader unlocking erases user data and permanently trips Knox when unauthorized software is flashed. Back up everything before proceeding.

## 2. Unlock the bootloader

1. Open Settings → About phone → Software information.
2. Tap Build number seven times.
3. Open Developer options.
4. Enable OEM unlocking and USB debugging.
5. Power off the phone.
6. Hold both volume buttons while connecting the USB cable.
7. Enter Download Mode.
8. Long-press Volume Up to unlock the bootloader.
9. Confirm the factory reset.
10. Complete Android setup and verify that the bootloader is unlocked.

## 3. Install the custom bootloader

1. Obtain the compatible UniLoader/LK3rd image for SM-G985F.
2. Enter Samsung Download Mode.
3. Flash the required bootloader package using the supported flashing utility.
4. Boot into LK3rd fastboot mode.
5. Verify connectivity:

```bash
fastboot devices
```

## 4. Boot native Linux

1. Build the NAOMI kernel and compatible boot image.
2. Verify the image checksum.
3. Enter LK3rd fastboot mode.
4. Flash the verified Linux boot image:

```bash
fastboot flash boot boot.img
fastboot reboot
```

## 5. Install Debian

1. Boot the Linux recovery environment.
2. Connect through USB serial or USB Ethernet.
3. Identify the target storage partition.
4. Install the Debian 13 ARM64 root filesystem.
5. Configure the root filesystem PARTUUID in the boot image.
6. Reboot into native Debian.

## 6. Install NAOMI userspace

Install the touchscreen, keyboard, OLED control, hardware monitoring, MOTD and TUI components using the supplied build and installation scripts.

## 7. Verify installation

```bash
uname -r
hostname
systemctl --failed
```

Launch the interactive interface:

```bash
naomi-tui-launch
```
