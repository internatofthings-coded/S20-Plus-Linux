#!/bin/sh
# Complete rollback for Bundle B (removes P07 binary/theme and P08 integration scripts).
# Leaves Bundle A (MOTD/artwork), P00-P06 services, PAM, SSH, and kernel untouched.
set -eu

rm -f /etc/profile.d/99-boros-tui.sh \
      /usr/local/bin/naomi-tui-launch \
      /usr/local/bin/naomi-tui \
      /etc/boros/tui.conf \
      /etc/boros/tui-theme.conf \
      /etc/boros/no-tui

rmdir /etc/boros 2>/dev/null || true

echo "Bundle B rolled back cleanly (Bundle A MOTD and P00-P06 untouched)."
