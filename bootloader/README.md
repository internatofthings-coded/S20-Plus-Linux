# Bootloader integration — provenance pending

The prototype uses a modified uniLoader-based boot path with a Linux Image, device tree and initramfs. The original release notes referred to [SoMainline/uniLoader](https://github.com/SoMainline/uniLoader), but the exact upstream fork and commit could not be verified during documentation review.

The actual modified bootloader source, local patches, initramfs build materials, lk3rd integration and boot image packaging parameters are not included. Recover these from the tested development tree, verify the applicable licenses and record the exact commands and hashes before publishing a boot recipe.

Do not use a generic mkbootimg configuration or an image for another Galaxy S20 model. This snapshot is not a flashable release. Retain a known-good recovery image and verify the recovery path before changing any partitions.
