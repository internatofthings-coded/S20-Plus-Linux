#!/bin/sh
# NAOMI P09 — Consolidated Live Qualification Script (run on NAOMI as root)
set -eu

PASS=0
FAIL=0

check() {
  desc="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "PASS: $desc"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $desc"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== NAOMI P09 Live Qualification ($(date -Iseconds)) ==="

# 1. Baseline & Kernel
check "Boot-052 kernel active (6.12.119-g970959bbf675)" test "$(uname -r)" = "6.12.119-g970959bbf675"
check "Hostname is naomi" test "$(hostname)" = "naomi"
check "Zero failed systemd units" test "$(systemctl --failed --no-legend | wc -l)" -eq 0
check "SSH daemon active" systemctl is-active --quiet ssh

# 2. P01 Touchscreen & P02 Buffyboard + Logout Redraw Fix
check "boros-touch.service active" systemctl is-active --quiet boros-touch.service
check "/dev/input/boros-touch exists" test -e /dev/input/boros-touch
check "boros-uinput.service active" systemctl is-active --quiet boros-uinput.service
check "/dev/uinput mode 660 group buffyboard" sh -c 'test "$(stat -c "%a:%G" /dev/uinput)" = "660:buffyboard"'
check "/dev/input/boros-touch mode 660 group buffyboard" sh -c 'test "$(stat -L -c "%a:%G" /dev/input/boros-touch)" = "660:buffyboard"'
check "boros-buffyboard.service active" systemctl is-active --quiet boros-buffyboard.service

# 3. P03 OLED & Power-Button Daemon
check "boros-oled.service active" systemctl is-active --quiet boros-oled.service
check "/sys/kernel/boros_oled/power exists" test -e /sys/kernel/boros_oled/power
check "boros-powerkeyd.service active" systemctl is-active --quiet boros-powerkeyd.service
check "logind powerkey drop-in installed" test -f /etc/systemd/logind.conf.d/10-boros-powerkey.conf

# 4. P04 Telemetry & Health Monitoring
check "boros-health.timer active" systemctl is-active --quiet boros-health.timer
check "/run/boros-health.json exists" test -s /run/boros-health.json
check "boros-telemetry --json succeeds" /usr/local/bin/boros-telemetry --json

# 5. P05/P06 Dynamic MOTD & NAOMI Artwork
check "/usr/local/bin/boros-motd executable" test -x /usr/local/bin/boros-motd
check "/etc/profile.d/99-boros-motd.sh installed" test -r /etc/profile.d/99-boros-motd.sh
check "NAOMI artwork files present" test -r /usr/local/share/boros/art/ouroboros-wide.txt

# 6. P07/P08 TUI Foundation & Terminal Integration
check "/usr/local/bin/naomi-tui executable" test -x /usr/local/bin/naomi-tui
check "naomi-tui --version succeeds" /usr/local/bin/naomi-tui --version
check "/usr/local/bin/naomi-tui-launch executable" test -x /usr/local/bin/naomi-tui-launch
check "/etc/profile.d/99-boros-tui.sh installed" test -r /etc/profile.d/99-boros-tui.sh
check "Noninteractive profile.d hooks emit 0 bytes" sh -c 'test -z "$(sh -c ". /etc/profile.d/99-boros-motd.sh; . /etc/profile.d/99-boros-tui.sh")"'

echo "=== Summary: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ]
