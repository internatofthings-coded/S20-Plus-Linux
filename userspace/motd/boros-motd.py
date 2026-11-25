#!/usr/bin/env python3
"""BOROS P05/P06 Dynamic MOTD & Custom ANSI Ouroboros Artwork Renderer.

Stdlib-only. Reuses boros_sysinfo and P04 /run/boros-health.json without
additional daemons. Supports responsive widths, ANSI color, monochrome, and
pure ASCII fallback, and always resets ANSI formatting.
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time

# Allow importing boros_sysinfo from installed lib dir or repo dir
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in ("/usr/local/lib/boros", _SCRIPT_DIR):
    if _p not in sys.path and os.path.isdir(_p):
        sys.path.insert(0, _p)

import boros_sysinfo  # noqa: E402

DEFAULT_ART_DIR = "/usr/local/share/boros/art"
_REPO_ART_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "p06"))

ANSI = {
    "0": "\x1b[0m",
    "R": "\x1b[1;31m",   # bright red
    "DR": "\x1b[31m",    # dark red
    "G": "\x1b[1;32m",   # green
    "Y": "\x1b[1;33m",   # yellow
    "C": "\x1b[1;36m",   # cyan
    "W": "\x1b[1;37m",   # bold white
    "D": "\x1b[90m",     # dim gray
}
_TOKEN_RE = re.compile(r"\{([A-Z0]+)\}")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def detect_color(mode="auto"):
    if mode == "always":
        return True
    if mode == "never":
        return False
    if os.environ.get("NO_COLOR") is not None:
        return False
    term = os.environ.get("TERM", "")
    if not term or term == "dumb":
        return False
    return sys.stdout.isatty()


def detect_utf8(force_ascii=False):
    if force_ascii:
        return False
    enc = (sys.stdout.encoding or "").lower()
    if "utf" in enc:
        return True
    for var in ("LC_ALL", "LC_CTYPE", "LANG"):
        val = os.environ.get(var, "").lower()
        if "utf-8" in val or "utf8" in val:
            return True
    return False


def detect_width(override=None):
    if override is not None and override > 0:
        return override
    return shutil.get_terminal_size(fallback=(80, 24)).columns


def resolve_art_dir(art_dir=None):
    if art_dir and os.path.isdir(art_dir):
        return art_dir
    if os.path.isdir(DEFAULT_ART_DIR):
        return DEFAULT_ART_DIR
    if os.path.isdir(_REPO_ART_DIR):
        return _REPO_ART_DIR
    return None


def style_tokens(text, use_color):
    if not use_color:
        return _TOKEN_RE.sub("", text)
    out = _TOKEN_RE.sub(lambda m: ANSI.get(m.group(1), ""), text)
    return out


def render_art(width, use_color, use_utf8, art_dir=None):
    adir = resolve_art_dir(art_dir)
    if not use_utf8:
        fname = "ouroboros-ascii.txt" if width >= 46 else "ouroboros-mini.txt"
    elif width >= 72:
        fname = "ouroboros-wide.txt"
    elif width >= 44:
        fname = "ouroboros-compact.txt"
    else:
        fname = "ouroboros-mini.txt"

    raw = None
    if adir:
        path = os.path.join(adir, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read().rstrip("\n")
        except OSError:
            raw = None

    if raw is None:
        raw = "{DR}(==={R}o<{W}--{DR}===) {R}NAOMI{0}"

    lines = []
    for line in raw.splitlines():
        styled = style_tokens(line, use_color)
        if use_color and not styled.endswith(ANSI["0"]):
            styled += ANSI["0"]
        lines.append(styled)
    return "\n".join(lines)


def fmt_duration(seconds):
    if seconds is None:
        return "N/A"
    s = int(seconds)
    days, rem = divmod(s, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if mins or hours or days:
        parts.append(f"{mins}m")
    if not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _c(code, text, use_color):
    if not use_color:
        return text
    return f"{ANSI[code]}{text}{ANSI['0']}"


def _status_color(status):
    if status == "OK":
        return "G"
    if status in ("WARN", "DEGRADED", "STALE") or "WARN" in status or "STALE" in status:
        return "Y"
    return "R"


def _fmt_temp(thermals, key, use_utf8):
    val = thermals.get(key)
    deg = "°C" if use_utf8 else "C"
    return f"{val:.1f}{deg}" if isinstance(val, (int, float)) else "N/A"


def render_stats(data, width, use_color, use_utf8):
    sys_d = data["system"]
    hw_d = data["hardware"]
    hl_d = data["health"]
    batt = hw_d.get("battery") or {}
    therm = hw_d.get("thermals_c") or {}

    sep = "─" if use_utf8 else "-"
    deg = "°C" if use_utf8 else "C"
    rule_w = max(32, min(width, 72))
    rule = _c("D", sep * rule_w, use_color)

    # System fields
    host_os = f"{sys_d['hostname']} | {sys_d['os']}"
    kern_arch = f"{sys_d['kernel']} ({sys_d['arch']})"
    uptime = fmt_duration(sys_d.get("uptime_s"))

    cpu = sys_d["cpu"]
    cpu_pct = f"{cpu['util_pct']:.1f}%" if cpu.get("util_pct") is not None else "N/A"
    cores = f"{cpu['cores_online']} cores" if cpu.get("cores_online") is not None else "N/A"
    load_s = f" (load {cpu['load_1m']:.2f})" if cpu.get("load_1m") is not None else ""
    cpu_str = f"{cpu_pct} | {cores}{load_s}"

    mem = sys_d["memory"]
    if mem.get("used_pct") is not None:
        mem_str = f"{mem['used_pct']:.1f}% ({mem['avail_mb']:.0f} MB avail / {mem['total_mb']:.0f} MB)"
    else:
        mem_str = "N/A"

    rfs = sys_d["root_fs"]
    if rfs.get("used_pct") is not None:
        fs_str = f"{rfs['used_pct']:.1f}% ({rfs['used_gb']:.1f} / {rfs['total_gb']:.1f} GiB)"
    else:
        fs_str = "N/A"

    # Hardware fields
    cap = f"{batt['capacity_pct']}%" if batt.get("capacity_pct") is not None else "N/A"
    bstat = batt.get("status") or "N/A"
    bhlth = batt.get("health") or "N/A"
    btemp = f"{batt['temp_c']:.1f}{deg}" if batt.get("temp_c") is not None else "N/A"
    bvolt = f"{batt['voltage_v']:.3f}V" if batt.get("voltage_v") is not None else "N/A"
    bcurr = f"{batt['current_ma']:+.1f}mA" if batt.get("current_ma") is not None else "N/A"

    batt_str = f"{cap} | {bstat} | Health: {bhlth}"
    batt_elec = f"{btemp} | {bvolt} | {bcurr}"
    cpu_temps = (
        f"Big {_fmt_temp(therm, 'big-thermal', use_utf8)} | "
        f"Mid {_fmt_temp(therm, 'mid-thermal', use_utf8)} | "
        f"Lit {_fmt_temp(therm, 'little-thermal', use_utf8)}"
    )
    soc_temps = (
        f"GPU {_fmt_temp(therm, 'gpu-thermal', use_utf8)} | "
        f"ISP {_fmt_temp(therm, 'isp-thermal', use_utf8)} | "
        f"NPU {_fmt_temp(therm, 'npu-thermal', use_utf8)}"
    )

    # Health fields
    overall = hl_d.get("overall", "UNKNOWN")
    cstatus = hl_d.get("cache_status", "MISSING")
    cage = hl_d.get("cache_age_s")
    if cstatus == "FRESH":
        cache_note = f" (cache {cage}s ago)" if cage is not None else ""
    elif cstatus == "STALE":
        cache_note = f" [STALE: {fmt_duration(cage)} old]"
    elif cstatus == "MISSING":
        cache_note = " [TELEMETRY CACHE MISSING]"
    else:
        cache_note = " [TELEMETRY CACHE CORRUPT]"

    overall_str = _c(_status_color(overall), overall, use_color) + _c("D" if cstatus == "FRESH" else "Y", cache_note, use_color)

    alerts = hl_d.get("alerts") or {}
    if alerts:
        warn_str = _c("Y", ", ".join(f"{k}={v}" for k, v in sorted(alerts.items())), use_color)
    elif cstatus != "FRESH":
        warn_str = _c("Y", "Unavailable (telemetry not fresh)", use_color)
    else:
        warn_str = _c("G", "None", use_color)

    failed = hl_d.get("failed_services")
    if failed is None:
        svc_str = _c("D", "N/A (systemd unavailable)", use_color)
    elif not failed:
        svc_str = _c("G", "0 failed", use_color)
    else:
        svc_str = _c("R", f"{len(failed)} failed: {', '.join(failed[:5])}", use_color)

    def row(label, val):
        lbl = _c("R", f"{label:<9}", use_color) if width >= 50 else _c("R", f"{label}:", use_color)
        return f" {lbl} {val}"

    lines = [
        rule,
        row("System", host_os),
        row("Kernel", kern_arch),
        row("Uptime", uptime),
        row("CPU", cpu_str),
        row("Memory", mem_str),
        row("Root FS", fs_str),
        rule,
        row("Battery", batt_str),
        row("Power", batt_elec),
        row("CPU Temp", cpu_temps),
        row("SoC Temp", soc_temps),
        rule,
        row("Health", overall_str),
        row("Warnings", warn_str),
        row("Services", svc_str),
        rule,
    ]
    return "\n".join(lines)


def render_motd(data, width, use_color, use_utf8, art_dir=None):
    art = render_art(width, use_color, use_utf8, art_dir=art_dir)
    stats = render_stats(data, width, use_color, use_utf8)
    out = f"{art}\n{stats}"
    if use_color:
        out += ANSI["0"]
    return out


def self_test():
    """Offline verification of P05 & P06 requirements."""
    with tempfile.TemporaryDirectory(prefix="boros-motd-test-") as td:
        now = int(time.time())
        fresh_path = os.path.join(td, "fresh.json")
        stale_path = os.path.join(td, "stale.json")
        corrupt_path = os.path.join(td, "corrupt.json")
        missing_path = os.path.join(td, "missing.json")

        sample_telem = {
            "timestamp": now - 15,
            "battery": {
                "capacity_pct": 87,
                "status": "Charging",
                "health": "Good",
                "voltage_v": 4.352,
                "current_ma": 485.0,
                "temp_c": 29.4,
            },
            "charger": {"online": True, "status": "Charging"},
            "thermals_c": {
                "big-thermal": 42.1,
                "mid-thermal": 39.8,
                "little-thermal": 37.5,
                "gpu-thermal": 36.0,
                "isp-thermal": 34.2,
                "npu-thermal": 33.9,
            },
        }
        with open(fresh_path, "w", encoding="utf-8") as f:
            json.dump({"timestamp": now - 15, "overall": "OK", "alerts": {}, "telemetry": sample_telem}, f)
        with open(stale_path, "w", encoding="utf-8") as f:
            json.dump({"timestamp": now - 600, "overall": "OK", "alerts": {}, "telemetry": sample_telem}, f)
        with open(corrupt_path, "w", encoding="utf-8") as f:
            f.write("{corrupt json")

        # 1. Fresh data + multiple widths + color + ANSI reset
        d_fresh = boros_sysinfo.collect_all(health_cache=fresh_path, cpu_sample_ms=10, check_systemd=False, now=now)
        assert d_fresh["health"]["overall"] == "OK"
        assert d_fresh["health"]["cache_status"] == "FRESH"
        for w in (36, 52, 80, 120):
            out = render_motd(d_fresh, width=w, use_color=True, use_utf8=True)
            assert out.endswith(ANSI["0"]), f"ANSI reset missing at width {w}"
            assert "87%" in out and "42.1°C" in out and "GPU 36.0°C" in out

        # 2. Monochrome & ASCII fallback (no ANSI escapes, pure ASCII)
        out_mono = render_motd(d_fresh, width=80, use_color=False, use_utf8=False)
        assert "\x1b[" not in out_mono, "ANSI leaked in monochrome mode"
        assert all(ord(ch) < 128 for ch in out_mono), "Non-ASCII leaked in ASCII mode"
        assert "42.1C" in out_mono

        # 3. Stale data must NOT report OK
        d_stale = boros_sysinfo.collect_all(health_cache=stale_path, cpu_sample_ms=0, check_systemd=False, now=now)
        assert d_stale["health"]["cache_status"] == "STALE"
        assert d_stale["health"]["overall"] == "STALE"
        out_stale = render_motd(d_stale, width=80, use_color=False, use_utf8=True)
        assert "STALE" in out_stale

        # 4. Missing cache must NOT report OK or fabricate values
        d_miss = boros_sysinfo.collect_all(health_cache=missing_path, cpu_sample_ms=0, check_systemd=False, now=now)
        assert d_miss["health"]["cache_status"] == "MISSING"
        assert d_miss["health"]["overall"] == "UNKNOWN"
        out_miss = render_motd(d_miss, width=80, use_color=False, use_utf8=True)
        assert "MISSING" in out_miss and "N/A" in out_miss

        # 5. Corrupt cache must NOT crash or report OK
        d_corr = boros_sysinfo.collect_all(health_cache=corrupt_path, cpu_sample_ms=0, check_systemd=False, now=now)
        assert d_corr["health"]["cache_status"] == "CORRUPT"
        assert d_corr["health"]["overall"] == "UNKNOWN"
        out_corr = render_motd(d_corr, width=80, use_color=False, use_utf8=True)
        assert "CORRUPT" in out_corr

    print("boros-motd self-test OK (all 5 suites passed: fresh/widths/ANSI, mono/ASCII, stale, missing, corrupt)")


def main():
    ap = argparse.ArgumentParser(description="BOROS Dynamic MOTD & ANSI Artwork Renderer")
    ap.add_argument("--width", type=int, default=None, help="override terminal width")
    ap.add_argument("--color", choices=("auto", "always", "never"), default="auto")
    ap.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    ap.add_argument("--ascii", action="store_true", help="force pure ASCII fallback")
    ap.add_argument("--art-dir", default=None, help="override artwork directory")
    ap.add_argument("--health-cache", default=boros_sysinfo.DEFAULT_HEALTH_CACHE)
    ap.add_argument("--stale-seconds", type=int, default=boros_sysinfo.DEFAULT_STALE_SECONDS)
    ap.add_argument("--cpu-sample-ms", type=int, default=50)
    ap.add_argument("--no-systemd", action="store_true")
    ap.add_argument("--self-test", action="store_true", help="run offline verification suite")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return

    use_color = False if args.no_color else detect_color(args.color)
    use_utf8 = detect_utf8(force_ascii=args.ascii)
    width = detect_width(args.width)
    data = boros_sysinfo.collect_all(
        health_cache=args.health_cache,
        stale_after_s=args.stale_seconds,
        cpu_sample_ms=args.cpu_sample_ms,
        check_systemd=not args.no_systemd,
    )
    print(render_motd(data, width=width, use_color=use_color, use_utf8=use_utf8, art_dir=args.art_dir))


if __name__ == "__main__":
    main()
