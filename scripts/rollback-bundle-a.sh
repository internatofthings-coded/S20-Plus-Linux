#!/bin/sh
# Complete rollback for Bundle A (restores hostname boros + removes MOTD/artwork)
# Leaves P00-P04 services, user ouro, PAM, SSH, and kernel untouched.
set -eu

# 1. Restore hostname to boros and revert /etc/hosts
hostnamectl set-hostname boros
if grep -qE '^[[:space:]]*127\.0\.1\.1[[:space:]]' /etc/hosts; then
  sed -i -E 's/^([[:space:]]*127\.0\.1\.1[[:space:]]+).*$/\1boros/' /etc/hosts
fi

# 2. Remove Bundle A files
rm -f /etc/profile.d/99-boros-motd.sh \
      /usr/local/bin/boros-motd \
      /usr/local/lib/boros/boros_sysinfo.py \
      /usr/local/share/boros/art/ouroboros-wide.txt \
      /usr/local/share/boros/art/ouroboros-compact.txt \
      /usr/local/share/boros/art/ouroboros-ascii.txt \
      /usr/local/share/boros/art/ouroboros-mini.txt

rmdir /usr/local/share/boros/art 2>/dev/null || true
rmdir /usr/local/share/boros 2>/dev/null || true
rmdir /usr/local/lib/boros 2>/dev/null || true

echo "Bundle A rolled back cleanly (hostname restored to boros)."
