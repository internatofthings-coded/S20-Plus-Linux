#!/bin/sh
# Idempotent installer for Bundle B (P07 NAOMI TUI + P08 Terminal Integration)
# Preserves Bundle A MOTD, P00-P06 services, PAM, SSH, and kernel untouched.
set -eu

SRC_DIR="${1:-/tmp/boros-bundle-b}"

install -d -m 0755 /etc/boros

if [ -f "$SRC_DIR/naomi-tui" ]; then
  install -D -m 0755 "$SRC_DIR/naomi-tui" /usr/local/bin/naomi-tui
else
  echo "WARNING: $SRC_DIR/naomi-tui binary not found; installing integration scripts only." >&2
fi

install -D -m 0755 "$SRC_DIR/naomi-tui-launch" /usr/local/bin/naomi-tui-launch
install -D -m 0644 "$SRC_DIR/99-boros-tui.sh" /etc/profile.d/99-boros-tui.sh

# Preserve existing owner config if already customized.
if [ ! -f /etc/boros/tui.conf ]; then
  install -D -m 0644 "$SRC_DIR/tui.conf" /etc/boros/tui.conf
fi
if [ ! -f /etc/boros/tui-theme.conf ]; then
  install -D -m 0644 "$SRC_DIR/tui-theme.conf" /etc/boros/tui-theme.conf
fi

echo "Bundle B (NAOMI TUI + Terminal Integration) installed cleanly."
echo "Run 'naomi-tui-launch' to start manually, or set AUTO_LAUNCH=1 in /etc/boros/tui.conf."
