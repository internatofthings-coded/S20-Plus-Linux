#!/usr/bin/env bash
# Isolated LiBox builder: backports Debian's official buffybox (postmarketOS upstream)
# to a clean Debian 13 (Trixie) ARM64 .deb package. Zero testing/sid repos touch BOROS.
set -euo pipefail

OUT_DIR="${1:-$HOME/s20-flash/p02-buffyboard}"
mkdir -p "$OUT_DIR"

if [ ! -e /proc/sys/fs/binfmt_misc/qemu-aarch64 ] && [ ! -e /proc/sys/fs/binfmt_misc/qemu-aarch64-static ]; then
  echo "WARNING: qemu-aarch64 binfmt_misc handler not detected on LiBox." >&2
  echo "Install qemu-user-static on LiBox (e.g. sudo dnf install qemu-user-static-aarch64) before running." >&2
fi

podman run --rm --platform linux/arm64 -v "$OUT_DIR:/out:Z" debian:trixie bash -euo pipefail -c '
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    devscripts debhelper-compat meson ninja-build pkg-config gcc git ca-certificates \
    libinput-dev libudev-dev libxkbcommon-dev libinih-dev scdoc

  echo "deb-src http://deb.debian.org/debian sid main" > /etc/apt/sources.list.d/sid-src.list
  apt-get update

  mkdir -p /tmp/src && cd /tmp/src
  apt-get source buffybox
  cd buffybox-*
  dpkg-buildpackage -us -uc -b

  cp /tmp/src/buffyboard_*_arm64.deb /out/
  sha256sum /out/buffyboard_*_arm64.deb | tee /out/SHA256SUMS
'

echo "Built Trixie ARM64 package(s) in: $OUT_DIR"
