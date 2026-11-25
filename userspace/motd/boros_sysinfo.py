#!/usr/bin/env python3
"""BOROS P05 reusable system statistics collector & P04 health cache reader.

Stdlib-only. Reads Linux /proc, /sys, statvfs, and the existing P04
/run/boros-health.json cache without adding daemons or fabricating data.
Designed for reuse by P05 MOTD and future P07 TUI.
"""

import argparse
import json
import os
import platform
import socket
import subprocess
import time

DEFAULT_HEALTH_CACHE = "/run/boros-health.json"
DEFAULT_STALE_SECONDS = 180  # 3x the 60s boros-health.timer interval


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def read_os_name(os_release_path="/etc/os-release"):
    txt = _read_text(os_release_path)
    if txt:
        for line in txt.splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')
    return f"{platform.system()} {platform.release()}"


def read_uptime_s(proc_root="/proc"):
    txt = _read_text(os.path.join(proc_root, "uptime"))
    if not txt:
        return None
    try:
        return int(float(txt.split()[0]))
    except (ValueError, IndexError):
        return None


def _read_cpu_times(proc_root="/proc"):
    txt = _read_text(os.path.join(proc_root, "stat"))
    if not txt:
        return None
    for line in txt.splitlines():
        if line.startswith("cpu "):
            parts = line.split()[1:]
            try:
                vals = [int(x) for x in parts]
            except ValueError:
                return None
            if len(vals) < 4:
                return None
            idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
            total = sum(vals)
            return idle, total
    return None


def read_cpu_info(proc_root="/proc", sample_ms=50):
    cores = os.cpu_count()
    try:
        load_1m, load_5m, load_15m = os.getloadavg()
    except OSError:
        load_1m = load_5m = load_15m = None

    util_pct = None
    if sample_ms > 0:
        t1 = _read_cpu_times(proc_root)
        if t1 is not None:
            time.sleep(sample_ms / 1000.0)
            t2 = _read_cpu_times(proc_root)
            if t2 is not None:
                d_total = t2[1] - t1[1]
                d_idle = t2[0] - t1[0]
                if d_total > 0:
                    util_pct = round(max(0.0, min(100.0, 100.0 * (1.0 - d_idle / d_total))), 1)

    return {
        "cores_online": cores,
        "util_pct": util_pct,
        "load_1m": round(load_1m, 2) if load_1m is not None else None,
        "load_5m": round(load_5m, 2) if load_5m is not None else None,
        "load_15m": round(load_15m, 2) if load_15m is not None else None,
    }


def read_memory_info(proc_root="/proc"):
    txt = _read_text(os.path.join(proc_root, "meminfo"))
    if not txt:
        return {"total_mb": None, "avail_mb": None, "used_mb": None, "used_pct": None}
    kv = {}
    for line in txt.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        parts = v.strip().split()
        if parts:
            try:
                kv[k] = int(parts[0])  # kB
            except ValueError:
                pass
    total_kb = kv.get("MemTotal")
    avail_kb = kv.get("MemAvailable")
    if total_kb is None or total_kb <= 0:
        return {"total_mb": None, "avail_mb": None, "used_mb": None, "used_pct": None}
    total_mb = round(total_kb / 1024.0, 1)
    if avail_kb is None:
        return {"total_mb": total_mb, "avail_mb": None, "used_mb": None, "used_pct": None}
    used_kb = max(0, total_kb - avail_kb)
    return {
        "total_mb": total_mb,
        "avail_mb": round(avail_kb / 1024.0, 1),
        "used_mb": round(used_kb / 1024.0, 1),
        "used_pct": round(100.0 * used_kb / total_kb, 1),
    }


def read_root_fs(path="/"):
    try:
        st = os.statvfs(path)
    except OSError:
        return {"total_gb": None, "used_gb": None, "avail_gb": None, "used_pct": None}
    total = st.f_blocks * st.f_frsize
    if total <= 0:
        return {"total_gb": None, "used_gb": None, "avail_gb": None, "used_pct": None}
    avail = st.f_bavail * st.f_frsize
    free = st.f_bfree * st.f_frsize
    used = max(0, total - free)
    gib = 1024.0 ** 3
    return {
        "total_gb": round(total / gib, 1),
        "used_gb": round(used / gib, 1),
        "avail_gb": round(avail / gib, 1),
        "used_pct": round(100.0 * used / total, 1),
    }


def read_failed_services(timeout_s=0.5):
    """Return list of failed systemd unit names, or None if systemd is unavailable."""
    try:
        res = subprocess.run(
            ["systemctl", "--failed", "--no-legend", "--no-pager", "--plain"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode != 0:
        return None
    units = []
    for line in res.stdout.splitlines():
        parts = line.split()
        if parts:
            units.append(parts[0])
    return units


def read_health_cache(cache_path=DEFAULT_HEALTH_CACHE, stale_after_s=DEFAULT_STALE_SECONDS, now=None):
    """Read P04 /run/boros-health.json with explicit missing, corrupt and stale handling."""
    now_ts = int(time.time()) if now is None else int(now)
    base = {
        "cache_status": "MISSING",
        "cache_path": cache_path,
        "timestamp": None,
        "age_s": None,
        "overall": "UNKNOWN",
        "alerts": {},
        "battery": {},
        "charger": {},
        "thermals_c": {},
    }
    if not cache_path or not os.path.exists(cache_path):
        return base

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        base["cache_status"] = "CORRUPT"
        return base

    if not isinstance(data, dict) or not isinstance(data.get("telemetry"), dict):
        base["cache_status"] = "CORRUPT"
        return base

    ts = data.get("timestamp")
    if not isinstance(ts, (int, float)):
        base["cache_status"] = "CORRUPT"
        return base

    age_s = max(0, now_ts - int(ts))
    is_stale = age_s > stale_after_s
    raw_overall = data.get("overall") if isinstance(data.get("overall"), str) else "UNKNOWN"
    overall = "STALE" if (is_stale and raw_overall == "OK") else (f"{raw_overall}/STALE" if is_stale else raw_overall)

    telem = data["telemetry"]
    alerts = data.get("alerts") if isinstance(data.get("alerts"), dict) else {}
    return {
        "cache_status": "STALE" if is_stale else "FRESH",
        "cache_path": cache_path,
        "timestamp": int(ts),
        "age_s": age_s,
        "overall": overall,
        "alerts": alerts,
        "battery": telem.get("battery") if isinstance(telem.get("battery"), dict) else {},
        "charger": telem.get("charger") if isinstance(telem.get("charger"), dict) else {},
        "thermals_c": telem.get("thermals_c") if isinstance(telem.get("thermals_c"), dict) else {},
    }


def collect_all(
    health_cache=DEFAULT_HEALTH_CACHE,
    stale_after_s=DEFAULT_STALE_SECONDS,
    cpu_sample_ms=50,
    check_systemd=True,
    proc_root="/proc",
    os_release_path="/etc/os-release",
    root_path="/",
    now=None,
):
    uname = os.uname()
    health = read_health_cache(health_cache, stale_after_s=stale_after_s, now=now)
    failed = read_failed_services() if check_systemd else None

    overall = health["overall"]
    if failed and overall == "OK":
        overall = "DEGRADED"

    return {
        "system": {
            "hostname": socket.gethostname(),
            "os": read_os_name(os_release_path),
            "kernel": uname.release,
            "arch": uname.machine,
            "uptime_s": read_uptime_s(proc_root),
            "cpu": read_cpu_info(proc_root, sample_ms=cpu_sample_ms),
            "memory": read_memory_info(proc_root),
            "root_fs": read_root_fs(root_path),
        },
        "hardware": {
            "battery": health["battery"],
            "charger": health["charger"],
            "thermals_c": health["thermals_c"],
        },
        "health": {
            "overall": overall,
            "cache_status": health["cache_status"],
            "cache_age_s": health["age_s"],
            "alerts": health["alerts"],
            "failed_services": failed,
        },
    }


def main():
    ap = argparse.ArgumentParser(description="BOROS system & health statistics collector")
    ap.add_argument("--health-cache", default=DEFAULT_HEALTH_CACHE)
    ap.add_argument("--stale-seconds", type=int, default=DEFAULT_STALE_SECONDS)
    ap.add_argument("--cpu-sample-ms", type=int, default=50)
    ap.add_argument("--no-systemd", action="store_true")
    args = ap.parse_args()
    data = collect_all(
        health_cache=args.health_cache,
        stale_after_s=args.stale_seconds,
        cpu_sample_ms=args.cpu_sample_ms,
        check_systemd=not args.no_systemd,
    )
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
