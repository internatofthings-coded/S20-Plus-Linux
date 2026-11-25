#!/usr/bin/env python3
"""BOROS P04 hardware telemetry collector & lightweight health monitor.

Stdlib-only. Reads Linux power_supply and thermal sysfs interfaces, never
fabricates missing values, and logs only state transitions to journald.
Reusable JSON output for P05 MOTD and P07 TUI.
"""

import argparse
import glob
import json
import os
import sys
import tempfile
import time

DEFAULT_STATE_FILE = "/run/boros-health-state.json"

# Evidence-based thresholds aligned with Boot-052 DTS and max77705_charger.c
CPU_ZONES = ("big-thermal", "mid-thermal", "little-thermal")
SOC_OTHER_ZONES = ("gpu-thermal", "isp-thermal", "npu-thermal")

THRESHOLDS = {
    "cpu_warn_c": 70.0,        # 5 C below kernel passive throttle (75 C)
    "cpu_crit_c": 85.0,        # 20 C below kernel critical shutdown (105 C)
    "cpu_hyst_c": 5.0,
    "soc_other_warn_c": 80.0,  # 15 C below DTS hot trip (95 C)
    "soc_other_crit_c": 90.0,
    "soc_other_hyst_c": 5.0,
    "batt_high_warn_c": 38.0,  # 4 C below max77705_charger cutoff (42 C)
    "batt_high_crit_c": 42.0,
    "batt_low_warn_c": 5.0,    # 5 C above max77705_charger cold cutoff (0 C)
    "batt_low_crit_c": 0.0,
    "batt_temp_hyst_c": 2.0,
    "batt_cap_warn_pct": 20,
    "batt_cap_crit_pct": 10,
    "batt_cap_hyst_pct": 5,
    "batt_volt_low_warn_v": 3.45,
    "batt_volt_low_crit_v": 3.35,  # 50 mV above dead-volt (3.30 V)
    "batt_volt_high_crit_v": 4.42, # 20 mV above over-volt (4.40 V)
}


def read_str(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            val = f.read().strip()
            return val if val else None
    except OSError:
        return None


def read_int(path):
    raw = read_str(path)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def discover_power_supplies(sysfs_root="/sys"):
    ps_dir = os.path.join(sysfs_root, "class", "power_supply")
    battery_dir = None
    charger_dir = None
    if not os.path.isdir(ps_dir):
        return None, None
    entries = sorted(os.listdir(ps_dir))
    for name in entries:
        full = os.path.join(ps_dir, name)
        ptype = read_str(os.path.join(full, "type"))
        if name == "max170xx_battery" or (battery_dir is None and ptype == "Battery"):
            battery_dir = full
        elif name == "max77705-charger" or (charger_dir is None and ptype in ("Mains", "USB")):
            charger_dir = full
    return battery_dir, charger_dir


def collect_telemetry(sysfs_root="/sys"):
    now = int(time.time())
    batt_dir, chg_dir = discover_power_supplies(sysfs_root)

    battery = {
        "source": os.path.basename(batt_dir) if batt_dir else None,
        "capacity_pct": None,
        "status": None,
        "health": None,
        "voltage_v": None,
        "current_ma": None,
        "temp_c": None,
    }
    if batt_dir:
        battery["capacity_pct"] = read_int(os.path.join(batt_dir, "capacity"))
        battery["status"] = read_str(os.path.join(batt_dir, "status"))
        battery["health"] = read_str(os.path.join(batt_dir, "health"))
        uv = read_int(os.path.join(batt_dir, "voltage_now"))
        if uv is not None:
            battery["voltage_v"] = round(uv / 1_000_000.0, 4)
        ua = read_int(os.path.join(batt_dir, "current_now"))
        if ua is not None:
            battery["current_ma"] = round(ua / 1_000.0, 2)
        t_tenth = read_int(os.path.join(batt_dir, "temp"))
        if t_tenth is not None:
            battery["temp_c"] = round(t_tenth / 10.0, 1)

    charger = {
        "source": os.path.basename(chg_dir) if chg_dir else None,
        "online": None,
        "status": None,
        "health": None,
        "charge_voltage_v": None,
        "charge_current_a": None,
        "input_current_limit_a": None,
    }
    if chg_dir:
        on = read_int(os.path.join(chg_dir, "online"))
        if on is not None:
            charger["online"] = bool(on)
        charger["status"] = read_str(os.path.join(chg_dir, "status"))
        charger["health"] = read_str(os.path.join(chg_dir, "health"))
        cv = read_int(os.path.join(chg_dir, "constant_charge_voltage"))
        if cv is not None:
            charger["charge_voltage_v"] = round(cv / 1_000_000.0, 4)
        cc = read_int(os.path.join(chg_dir, "constant_charge_current"))
        if cc is not None:
            charger["charge_current_a"] = round(cc / 1_000_000.0, 3)
        icl = read_int(os.path.join(chg_dir, "input_current_limit"))
        if icl is not None:
            charger["input_current_limit_a"] = round(icl / 1_000_000.0, 3)

    thermals = {}
    tz_glob = os.path.join(sysfs_root, "class", "thermal", "thermal_zone*")
    for tz in sorted(glob.glob(tz_glob)):
        ztype = read_str(os.path.join(tz, "type"))
        if not ztype:
            continue
        mc = read_int(os.path.join(tz, "temp"))
        thermals[ztype] = round(mc / 1000.0, 1) if mc is not None else None

    return {
        "timestamp": now,
        "battery": battery,
        "charger": charger,
        "thermals_c": thermals,
    }


def _eval_high(val, warn, crit, hyst, prev_level):
    if val is None:
        return "UNKNOWN"
    if val >= crit:
        return "CRIT"
    if prev_level == "CRIT" and val >= (crit - hyst):
        return "CRIT"
    if val >= warn:
        return "WARN"
    if prev_level in ("WARN", "CRIT") and val >= (warn - hyst):
        return "WARN"
    return "OK"


def evaluate_health(telemetry, prev_alerts=None):
    """Return (overall_status, alerts_dict) with hysteresis against prev_alerts."""
    prev = prev_alerts or {}
    alerts = {}

    thermals = telemetry.get("thermals_c", {})
    for z in CPU_ZONES:
        if z in thermals:
            lvl = _eval_high(
                thermals[z],
                THRESHOLDS["cpu_warn_c"],
                THRESHOLDS["cpu_crit_c"],
                THRESHOLDS["cpu_hyst_c"],
                prev.get(f"thermal:{z}", "OK"),
            )
            if lvl != "OK":
                alerts[f"thermal:{z}"] = lvl

    for z in SOC_OTHER_ZONES:
        if z in thermals:
            lvl = _eval_high(
                thermals[z],
                THRESHOLDS["soc_other_warn_c"],
                THRESHOLDS["soc_other_crit_c"],
                THRESHOLDS["soc_other_hyst_c"],
                prev.get(f"thermal:{z}", "OK"),
            )
            if lvl != "OK":
                alerts[f"thermal:{z}"] = lvl

    batt = telemetry.get("battery", {})
    btemp = batt.get("temp_c")
    if btemp is not None:
        p = prev.get("battery:temp", "OK")
        if btemp >= THRESHOLDS["batt_high_crit_c"] or btemp <= THRESHOLDS["batt_low_crit_c"]:
            alerts["battery:temp"] = "CRIT"
        elif p == "CRIT" and (
            btemp >= THRESHOLDS["batt_high_crit_c"] - THRESHOLDS["batt_temp_hyst_c"]
            or btemp <= THRESHOLDS["batt_low_crit_c"] + THRESHOLDS["batt_temp_hyst_c"]
        ):
            alerts["battery:temp"] = "CRIT"
        elif btemp >= THRESHOLDS["batt_high_warn_c"] or btemp <= THRESHOLDS["batt_low_warn_c"]:
            alerts["battery:temp"] = "WARN"
        elif p in ("WARN", "CRIT") and (
            btemp >= THRESHOLDS["batt_high_warn_c"] - THRESHOLDS["batt_temp_hyst_c"]
            or btemp <= THRESHOLDS["batt_low_warn_c"] + THRESHOLDS["batt_temp_hyst_c"]
        ):
            alerts["battery:temp"] = "WARN"

    bhealth = batt.get("health")
    if bhealth is not None and bhealth != "Good":
        alerts["battery:health"] = "CRIT"

    bcap = batt.get("capacity_pct")
    bstatus = batt.get("status")
    if bcap is not None and bstatus == "Discharging":
        p = prev.get("battery:capacity", "OK")
        if bcap <= THRESHOLDS["batt_cap_crit_pct"]:
            alerts["battery:capacity"] = "CRIT"
        elif p == "CRIT" and bcap < THRESHOLDS["batt_cap_crit_pct"] + THRESHOLDS["batt_cap_hyst_pct"]:
            alerts["battery:capacity"] = "CRIT"
        elif bcap <= THRESHOLDS["batt_cap_warn_pct"]:
            alerts["battery:capacity"] = "WARN"
        elif p in ("WARN", "CRIT") and bcap < THRESHOLDS["batt_cap_warn_pct"] + THRESHOLDS["batt_cap_hyst_pct"]:
            alerts["battery:capacity"] = "WARN"

    bvolt = batt.get("voltage_v")
    if bvolt is not None:
        if bvolt <= THRESHOLDS["batt_volt_low_crit_v"] or bvolt >= THRESHOLDS["batt_volt_high_crit_v"]:
            alerts["battery:voltage"] = "CRIT"
        elif bvolt <= THRESHOLDS["batt_volt_low_warn_v"]:
            alerts["battery:voltage"] = "WARN"

    if any(v == "CRIT" for v in alerts.values()):
        overall = "CRIT"
    elif any(v == "WARN" for v in alerts.values()):
        overall = "WARN"
    elif any(v == "UNKNOWN" for v in alerts.values()):
        overall = "DEGRADED"
    else:
        overall = "OK"
    return overall, alerts


def atomic_write_json(path, payload):
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".boros-health-", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"))
            f.write("\n")
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def format_summary(telemetry, overall, alerts):
    b = telemetry["battery"]
    c = telemetry["charger"]
    t = telemetry["thermals_c"]
    cap = f"{b['capacity_pct']}%" if b["capacity_pct"] is not None else "N/A"
    volt = f"{b['voltage_v']:.3f}V" if b["voltage_v"] is not None else "N/A"
    curr = f"{b['current_ma']:.1f}mA" if b["current_ma"] is not None else "N/A"
    bt = f"{b['temp_c']:.1f}C" if b["temp_c"] is not None else "N/A"
    chg_on = "online" if c["online"] is True else ("offline" if c["online"] is False else "N/A")
    lines = [
        f"Health:  {overall}" + (f" ({', '.join(f'{k}={v}' for k, v in sorted(alerts.items()))})" if alerts else ""),
        f"Battery: {cap} | {b['status'] or 'N/A'} | {b['health'] or 'N/A'} | {volt} | {curr} | {bt}",
        f"Charger: {chg_on} | {c['status'] or 'N/A'}",
    ]
    if t:
        t_parts = [f"{k}={v:.1f}C" if v is not None else f"{k}=N/A" for k, v in sorted(t.items())]
        lines.append("Thermal: " + " | ".join(t_parts))
    else:
        lines.append("Thermal: N/A")
    return "\n".join(lines)


def run_check(sysfs_root, state_file, write_state):
    prev_state = {}
    if state_file and os.path.isfile(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                prev_state = json.load(f)
        except (OSError, ValueError):
            prev_state = {}

    prev_alerts = prev_state.get("alerts", {})
    prev_batt_status = prev_state.get("battery_status")
    telemetry = collect_telemetry(sysfs_root)
    overall, alerts = evaluate_health(telemetry, prev_alerts)

    # Log only state transitions to prevent journald flooding
    for key in sorted(set(prev_alerts) | set(alerts)):
        old = prev_alerts.get(key, "OK")
        new = alerts.get(key, "OK")
        if old != new:
            print(f"boros-health: {key} {old} -> {new}", flush=True)

    cur_batt_status = telemetry["battery"].get("status")
    if prev_batt_status is not None and cur_batt_status != prev_batt_status:
        print(
            f"boros-health: battery status {prev_batt_status} -> {cur_batt_status} "
            f"(cap={telemetry['battery'].get('capacity_pct')}%)",
            flush=True,
        )

    new_state = {
        "timestamp": telemetry["timestamp"],
        "overall": overall,
        "alerts": alerts,
        "battery_status": cur_batt_status,
        "telemetry": telemetry,
    }
    if state_file:
        atomic_write_json(state_file, new_state)
    if write_state and write_state != state_file:
        atomic_write_json(write_state, new_state)
    return 0


def self_test():
    """Offline unit & fault-injection tests with synthetic sysfs trees."""
    with tempfile.TemporaryDirectory(prefix="boros-telem-test-") as td:
        ps_b = os.path.join(td, "class", "power_supply", "max170xx_battery")
        ps_c = os.path.join(td, "class", "power_supply", "max77705-charger")
        tz0 = os.path.join(td, "class", "thermal", "thermal_zone0")
        tz1 = os.path.join(td, "class", "thermal", "thermal_zone1")
        tz2 = os.path.join(td, "class", "thermal", "thermal_zone2")
        for d in (ps_b, ps_c, tz0, tz1, tz2):
            os.makedirs(d)

        def wf(d, name, val):
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(str(val) + "\n")

        # 1. Valid nominal telemetry & unit conversions
        wf(ps_b, "type", "Battery")
        wf(ps_b, "capacity", "88")
        wf(ps_b, "status", "Charging")
        wf(ps_b, "health", "Good")
        wf(ps_b, "voltage_now", "4363000")
        wf(ps_b, "current_now", "512500")
        wf(ps_b, "temp", "295")
        wf(ps_c, "type", "Mains")
        wf(ps_c, "online", "1")
        wf(ps_c, "status", "Charging")
        wf(ps_c, "constant_charge_voltage", "4380000")
        wf(ps_c, "constant_charge_current", "1000000")
        wf(tz0, "type", "big-thermal")
        wf(tz0, "temp", "41000")
        wf(tz1, "type", "mid-thermal")
        wf(tz1, "temp", "39500")
        wf(tz2, "type", "max170xx_battery")
        wf(tz2, "temp", "29500")

        t = collect_telemetry(td)
        assert t["battery"]["capacity_pct"] == 88
        assert t["battery"]["voltage_v"] == 4.363
        assert t["battery"]["current_ma"] == 512.5
        assert t["battery"]["temp_c"] == 29.5
        assert t["charger"]["online"] is True
        assert t["charger"]["charge_voltage_v"] == 4.38
        assert t["thermals_c"]["big-thermal"] == 41.0
        overall, alerts = evaluate_health(t)
        assert overall == "OK" and alerts == {}, (overall, alerts)

        # 2. Threshold warning + hysteresis + recovery
        wf(tz0, "temp", "72000")  # >= 70 C -> WARN
        t = collect_telemetry(td)
        overall, alerts = evaluate_health(t, {})
        assert overall == "WARN" and alerts == {"thermal:big-thermal": "WARN"}

        wf(tz0, "temp", "67000")  # within 5 C hysteresis -> stays WARN
        t = collect_telemetry(td)
        overall, alerts = evaluate_health(t, {"thermal:big-thermal": "WARN"})
        assert overall == "WARN" and alerts == {"thermal:big-thermal": "WARN"}

        wf(tz0, "temp", "64000")  # below 65 C -> clears to OK
        t = collect_telemetry(td)
        overall, alerts = evaluate_health(t, {"thermal:big-thermal": "WARN"})
        assert overall == "OK" and alerts == {}

        # 3. Critical battery temp & low discharging capacity
        wf(ps_b, "temp", "425")  # 42.5 C -> CRIT
        wf(ps_b, "status", "Discharging")
        wf(ps_b, "capacity", "9")
        t = collect_telemetry(td)
        overall, alerts = evaluate_health(t)
        assert overall == "CRIT"
        assert alerts["battery:temp"] == "CRIT"
        assert alerts["battery:capacity"] == "CRIT"

        # 4. Missing / corrupt sensors -> None (never fabricated)
        os.unlink(os.path.join(ps_b, "current_now"))
        wf(tz1, "temp", "NOT_A_NUMBER")
        t = collect_telemetry(td)
        assert t["battery"]["current_ma"] is None
        assert t["thermals_c"]["mid-thermal"] is None

        # 5. Completely missing sysfs -> graceful None, no crash
        empty = os.path.join(td, "empty_sys")
        t_empty = collect_telemetry(empty)
        assert t_empty["battery"]["capacity_pct"] is None
        assert t_empty["thermals_c"] == {}

    print("boros-telemetry self-test OK (all 5 telemetry, hysteresis & fault-injection suites passed)")


def main():
    ap = argparse.ArgumentParser(description="BOROS hardware telemetry & health monitor")
    ap.add_argument("--sysfs", default="/sys", help="sysfs root (for testing)")
    ap.add_argument("--json", action="store_true", help="output JSON snapshot")
    ap.add_argument("--check", action="store_true", help="evaluate thresholds & log transitions")
    ap.add_argument("--state-file", default=DEFAULT_STATE_FILE, help="state cache path for --check")
    ap.add_argument("--write-state", default=None, help="optional additional JSON snapshot output")
    ap.add_argument("--self-test", action="store_true", help="run offline unit & fault-injection tests")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    if args.check:
        sys.exit(run_check(args.sysfs, args.state_file, args.write_state))

    telemetry = collect_telemetry(args.sysfs)
    overall, alerts = evaluate_health(telemetry)
    if args.json:
        print(json.dumps({"overall": overall, "alerts": alerts, **telemetry}, separators=(",", ":")))
    else:
        print(format_summary(telemetry, overall, alerts))


if __name__ == "__main__":
    main()
