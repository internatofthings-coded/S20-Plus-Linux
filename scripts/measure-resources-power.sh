#!/bin/sh
# NAOMI P09 — Passive Resource & Power Consumption Measurement Procedure
# Run on NAOMI as root. Strictly passive observation; NO stress testing.
set -eu

echo "=== NAOMI P09 Resource & Power Baseline ($(date -Iseconds)) ==="

echo "--- 1. Service Memory & CPU Accounting ---"
for unit in boros-buffyboard.service boros-powerkeyd.service boros-health.service; do
  echo "[$unit]"
  systemctl show "$unit" -p ActiveState -p MemoryCurrent -p MemoryPeak -p MemoryMax -p CPUUsageNSec 2>/dev/null || true
done

echo "--- 2. Oneshot Latency & Peak RSS ---"
if [ -x /usr/bin/time ]; then
  echo "[boros-telemetry --json]"
  /usr/bin/time -f "elapsed=%es maxrss=%MKB" /usr/local/bin/boros-telemetry --json >/dev/null
  echo "[boros-motd]"
  /usr/bin/time -f "elapsed=%es maxrss=%MKB" /usr/local/bin/boros-motd >/dev/null
  echo "[naomi-tui --version]"
  /usr/bin/time -f "elapsed=%es maxrss=%MKB" /usr/local/bin/naomi-tui --version >/dev/null
else
  echo "NOTE: /usr/bin/time not installed; skipping maxrss measurement."
fi

echo "--- 3. Passive Power & Thermal Snapshot (OLED current state) ---"
cat /sys/kernel/boros_oled/status 2>/dev/null || echo "boros_oled status unavailable"
/usr/local/bin/boros-telemetry --json 2>/dev/null || true

echo "--- 4. Instructions for OLED-ON vs OLED-OFF Passive Power Delta ---"
echo "1. Record battery current_now above with OLED ON (unplugged on battery for accurate discharge delta)."
echo "2. Press physical Power button (<3s) to lock tty1 and turn OLED OFF."
echo "3. Wait 10 seconds, then over SSH run: /usr/local/bin/boros-telemetry --json"
echo "4. Compare battery.current_ma (OLED ON vs OLED OFF) and record in docs/boros-p09-checkpoint.md."
