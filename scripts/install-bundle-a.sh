#!/bin/sh
# Idempotent installer for Bundle A (P05 Dynamic MOTD + P06 NAOMI ANSI Artwork + hostname naomi)
set -eu

SRC_DIR="${1:-/tmp/boros-bundle-a}"

# 1. Set hostname to naomi and update /etc/hosts (preserves all internal boros paths/services)
hostnamectl set-hostname naomi
if grep -qE '^[[:space:]]*127\.0\.1\.1[[:space:]]' /etc/hosts; then
  sed -i -E 's/^([[:space:]]*127\.0\.1\.1[[:space:]]+).*$/\1naomi/' /etc/hosts
else
  printf '127.0.1.1\tnaomi\n' >> /etc/hosts
fi

# 2. Install Bundle A components
install -D -m 0755 "$SRC_DIR/boros_sysinfo.py" /usr/local/lib/boros/boros_sysinfo.py
install -D -m 0755 "$SRC_DIR/boros-motd.py" /usr/local/bin/boros-motd
install -D -m 0644 "$SRC_DIR/99-boros-motd.sh" /etc/profile.d/99-boros-motd.sh

install -d -m 0755 /usr/local/share/boros/art
install -D -m 0644 "$SRC_DIR/ouroboros-wide.txt" /usr/local/share/boros/art/ouroboros-wide.txt
install -D -m 0644 "$SRC_DIR/ouroboros-compact.txt" /usr/local/share/boros/art/ouroboros-compact.txt
install -D -m 0644 "$SRC_DIR/ouroboros-ascii.txt" /usr/local/share/boros/art/ouroboros-ascii.txt
install -D -m 0644 "$SRC_DIR/ouroboros-mini.txt" /usr/local/share/boros/art/ouroboros-mini.txt

echo "Bundle A (NAOMI branding + hostname naomi) installed cleanly."
