#!/usr/bin/env python3
"""BOROS power-button daemon: short-press OLED lock/wake + long-press graceful shutdown."""

import glob
import os
import selectors
import struct
import subprocess
import sys
import time

EV_KEY = 0x01
KEY_POWER = 116
EVENT_FMT = "qqHHi"
EVENT_SIZE = struct.calcsize(EVENT_FMT)

OLED_POWER_PATH = os.environ.get("BOROS_OLED_POWER", "/sys/kernel/boros_oled/power")
SHORT_PRESS_MAX_S = 3.0
# S20+ (S2MPS19) hardware forced reset is ~7s (Power+VolDown); 4.0s gives clear margin
LONG_PRESS_SHUTDOWN_S = 4.0
DEBOUNCE_S = 1.5
SELECT_POLL_S = 0.25
CMD_TIMEOUT_S = 10.0
TTY1_TERM_TIMEOUT_S = 5.0
TTY1_POLL_S = 0.2
WAKE_RETRIES = 2
WAKE_RETRY_DELAY_S = 0.3


def log(msg):
    print(f"boros-powerkeyd: {msg}", flush=True)


def find_powerkey_dev():
    env_dev = os.environ.get("BOROS_POWERKEY_DEV")
    if env_dev:
        return env_dev
    for name_path in sorted(glob.glob("/sys/class/input/event*/device/name")):
        try:
            with open(name_path, "r", encoding="utf-8") as f:
                if f.read().strip() == "gpio-keys":
                    ev = name_path.split("/")[4]
                    return f"/dev/input/{ev}"
        except OSError:
            continue
    raise FileNotFoundError("gpio-keys input device not found")


def run_cmd(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=CMD_TIMEOUT_S)
    except (subprocess.TimeoutExpired, OSError) as exc:
        log(f"command failed ({cmd}): {exc}")
        return subprocess.CompletedProcess(cmd, returncode=124, stdout="", stderr=str(exc))


def get_service_state(unit, runner=run_cmd):
    """Query explicit systemd ActiveState; returns None on error/timeout."""
    r = runner(["systemctl", "show", "-p", "ActiveState", "--value", unit])
    if r.returncode != 0:
        return None
    val = r.stdout.strip()
    return val if val else None


def parse_kv(text):
    props = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        props[k.strip()] = v.strip()
    return props


def list_tty1_sessions(runner=run_cmd):
    """Return tty1 session IDs using machine-readable loginctl show-session properties."""
    r = runner(["loginctl", "list-sessions", "--no-legend"])
    if r.returncode != 0:
        return None
    tty1_ids = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        sid = line.split()[0]
        sr = runner(["loginctl", "show-session", sid, "-p", "TTY", "-p", "State"])
        if sr.returncode != 0:
            return None
        props = parse_kv(sr.stdout)
        if "TTY" not in props or "State" not in props:
            log(f"error: malformed show-session output for {sid}")
            return None
        if props["TTY"] == "tty1":
            tty1_ids.append(sid)
    return tty1_ids


def lock_tty1(runner=run_cmd, sleep_fn=time.sleep, monotonic_fn=time.monotonic):
    """Terminate all tty1 sessions, verify termination and Buffyboard stop, ensure getty@tty1."""
    sessions = list_tty1_sessions(runner)
    if sessions is None:
        log("error: loginctl session query failed; aborting OLED off")
        return False

    had_sessions = bool(sessions)
    for sid in sessions:
        r = runner(["loginctl", "terminate-session", sid])
        if r.returncode != 0:
            log(f"warning: terminate-session {sid} returned {r.returncode}")

    deadline = monotonic_fn() + TTY1_TERM_TIMEOUT_S
    while sessions:
        if monotonic_fn() >= deadline:
            log(f"error: tty1 sessions {sessions} did not terminate within {TTY1_TERM_TIMEOUT_S}s")
            return False
        sleep_fn(TTY1_POLL_S)
        sessions = list_tty1_sessions(runner)
        if sessions is None:
            log("error: loginctl poll failed; aborting OLED off")
            return False

    r = runner(["systemctl", "stop", "boros-buffyboard.service"])
    if r.returncode != 0:
        log(f"error: boros-buffyboard stop failed (rc={r.returncode}); aborting OLED off")
        return False
    buffy_state = get_service_state("boros-buffyboard.service", runner)
    if buffy_state not in ("inactive", "failed"):
        log(f"error: boros-buffyboard state={buffy_state!r} after stop; aborting OLED off")
        return False

    # Only restart getty@tty1 if a session was terminated or getty is not active
    if had_sessions or get_service_state("getty@tty1.service", runner) != "active":
        r = runner(["systemctl", "restart", "getty@tty1.service"])
        if r.returncode != 0 or get_service_state("getty@tty1.service", runner) != "active":
            log(f"error: getty@tty1 restart failed (rc={r.returncode}); restoring buffyboard")
            runner(["systemctl", "start", "boros-buffyboard.service"])
            return False
    return True


def wake_tty1(runner=run_cmd, sleep_fn=time.sleep):
    """Ensure getty@tty1 is active and start Buffyboard OSK without redundant getty restarts."""
    if get_service_state("getty@tty1.service", runner) != "active":
        r1 = runner(["systemctl", "start", "getty@tty1.service"])
        if r1.returncode != 0 or get_service_state("getty@tty1.service", runner) != "active":
            log(f"error: getty@tty1 not active after wake (rc={r1.returncode})")
            return False
        sleep_fn(0.2)
    r2 = runner(["systemctl", "start", "boros-buffyboard.service"])
    if r2.returncode != 0 or get_service_state("boros-buffyboard.service", runner) != "active":
        log(f"error: boros-buffyboard not active after wake (rc={r2.returncode})")
        return False
    return True


def set_oled(on):
    with open(OLED_POWER_PATH, "w", encoding="utf-8") as f:
        f.write("1\n" if on else "0\n")


def read_oled(path=None):
    target = path or OLED_POWER_PATH
    try:
        with open(target, "r", encoding="utf-8") as f:
            val = f.read().strip()
    except OSError:
        return "fault"
    if val == "1":
        return "on"
    if val == "0":
        return "off"
    return "fault"


def handle_short_press(state, oled_fn=set_oled, runner=run_cmd,
                       sleep_fn=time.sleep, monotonic_fn=time.monotonic):
    now = monotonic_fn()
    if now - state["last_toggle"] < DEBOUNCE_S:
        log("debounced short press")
        return

    if state["mode"] == "on":
        log("short press: locking tty1 + OLED off")
        if not lock_tty1(runner=runner, sleep_fn=sleep_fn, monotonic_fn=monotonic_fn):
            state["last_toggle"] = monotonic_fn()
            return
        try:
            oled_fn(False)
            state["mode"] = "off"
        except OSError as exc:
            log(f"error: OLED off failed: {exc}; restoring tty1/buffyboard")
            state["mode"] = "fault"
            wake_tty1(runner=runner, sleep_fn=sleep_fn)
    else:
        log(f"short press (mode={state['mode']}): OLED on + redraw tty1/buffyboard")
        woke = False
        for attempt in range(1, WAKE_RETRIES + 1):
            try:
                oled_fn(True)
                woke = True
                break
            except OSError as exc:
                log(f"error: OLED wake attempt {attempt}/{WAKE_RETRIES} failed: {exc}")
                if attempt < WAKE_RETRIES:
                    sleep_fn(WAKE_RETRY_DELAY_S)
        if woke and wake_tty1(runner=runner, sleep_fn=sleep_fn):
            state["mode"] = "on"
        else:
            log("FAULT: wake or tty1/buffyboard restore failed; staying in fault state")
            state["mode"] = "fault"

    state["last_toggle"] = monotonic_fn()


def handle_long_press_shutdown(state, runner=run_cmd):
    """Trigger an orderly systemd shutdown once per intentional long press."""
    if state.get("shutting_down"):
        return False
    state["shutting_down"] = True
    log("long press (>=4.0s): initiating orderly systemd poweroff")
    r = runner(["systemctl", "poweroff"])
    if r.returncode != 0:
        log(f"error: systemctl poweroff failed (rc={r.returncode}): {r.stderr.strip()}")
        state["shutting_down"] = False
        return False
    return True


def process_key_event(sec, usec, etype, code, value, press_start, state, **kwargs):
    """Process one decoded input_event using kernel event timestamps."""
    if etype != EV_KEY or code != KEY_POWER:
        return press_start
    if state.get("shutting_down"):
        return None
    ev_ts = sec + (usec / 1_000_000.0)
    if value == 1:
        # Ignore duplicate key-down events while already pressed
        if press_start is None:
            return ev_ts
        return press_start
    if value == 2:
        # Ignore kernel key auto-repeat events
        return press_start
    if value == 0 and press_start is not None:
        held = ev_ts - press_start
        if 0.0 <= held < SHORT_PRESS_MAX_S:
            handle_short_press(state, **kwargs)
        elif held >= LONG_PRESS_SHUTDOWN_S:
            handle_long_press_shutdown(state, runner=kwargs.get("runner", run_cmd))
        else:
            log(f"ignored press in dead-zone (held={held:.2f}s)")
        return None
    return press_start


def check_hold_timeout(press_start_mono, state, monotonic_fn=time.monotonic, runner=run_cmd):
    """Trigger graceful shutdown as soon as a continuous hold reaches LONG_PRESS_SHUTDOWN_S."""
    if press_start_mono is None or state.get("shutting_down"):
        return False
    if monotonic_fn() - press_start_mono >= LONG_PRESS_SHUTDOWN_S:
        return handle_long_press_shutdown(state, runner=runner)
    return False


def self_test():
    """Offline static + expanded state-machine & fault-injection tests (13 scenarios)."""
    assert EVENT_SIZE == 24, f"expected 24-byte input_event, got {EVENT_SIZE}"
    raw = struct.pack(EVENT_FMT, 100, 500000, EV_KEY, KEY_POWER, 1)
    assert struct.unpack(EVENT_FMT, raw) == (100, 500000, EV_KEY, KEY_POWER, 1)

    t = [10.0]
    def fake_mono():
        return t[0]
    def fake_sleep(dt):
        t[0] += dt

    # 1. Verified tty1 termination + Buffyboard stop before OLED off
    active_sessions = [["42"]]
    svc_state = {"boros-buffyboard.service": "active", "getty@tty1.service": "active"}
    oled_calls = []
    def runner_ok(cmd):
        if cmd[:2] == ["loginctl", "list-sessions"]:
            out = "42 1000 user seat0 tty1\n" if active_sessions[0] else ""
            return subprocess.CompletedProcess(cmd, 0, out, "")
        if cmd[:2] == ["loginctl", "show-session"]:
            return subprocess.CompletedProcess(cmd, 0, "TTY=tty1\nState=active\n", "")
        if cmd[:2] == ["loginctl", "terminate-session"]:
            active_sessions[0] = []
        if cmd[:2] == ["systemctl", "stop"]:
            svc_state[cmd[2]] = "inactive"
        if cmd[:2] in (["systemctl", "start"], ["systemctl", "restart"]):
            svc_state[cmd[2]] = "active"
        if cmd[:2] == ["systemctl", "show"]:
            return subprocess.CompletedProcess(cmd, 0, svc_state[cmd[-1]] + "\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    st = {"mode": "on", "last_toggle": 0.0}
    handle_short_press(st, oled_fn=oled_calls.append, runner=runner_ok,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st["mode"] == "off" and oled_calls == [False], (st, oled_calls)

    # 2. Debounce ignores rapid second press
    handle_short_press(st, oled_fn=oled_calls.append, runner=runner_ok,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st["mode"] == "off" and oled_calls == [False]

    # 3. Wake failure enters fault, next press recovers to on
    t[0] += 2.0
    fail_wake = [True]
    def oled_flaky(on):
        oled_calls.append(on)
        if on and fail_wake[0]:
            raise OSError("ETIMEDOUT")

    handle_short_press(st, oled_fn=oled_flaky, runner=runner_ok,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st["mode"] == "fault", st

    t[0] += 2.0
    fail_wake[0] = False
    handle_short_press(st, oled_fn=oled_flaky, runner=runner_ok,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st["mode"] == "on", st

    # 4. Stuck tty1 session aborts OLED off (fail-closed)
    t[0] += 2.0
    oled_calls.clear()
    def runner_stuck(cmd):
        if cmd[:2] == ["loginctl", "list-sessions"]:
            return subprocess.CompletedProcess(cmd, 0, "99 1000 user seat0 tty1\n", "")
        if cmd[:2] == ["loginctl", "show-session"]:
            return subprocess.CompletedProcess(cmd, 0, "TTY=tty1\nState=active\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    handle_short_press(st, oled_fn=oled_calls.append, runner=runner_stuck,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st["mode"] == "on" and oled_calls == [], (st, oled_calls)

    # 5. Malformed show-session output aborts OLED off (fail-closed)
    t[0] += 2.0
    def runner_malformed(cmd):
        if cmd[:2] == ["loginctl", "list-sessions"]:
            return subprocess.CompletedProcess(cmd, 0, "55 1000 user\n", "")
        if cmd[:2] == ["loginctl", "show-session"]:
            return subprocess.CompletedProcess(cmd, 0, "GARBAGE_OUTPUT\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    handle_short_press(st, oled_fn=oled_calls.append, runner=runner_malformed,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st["mode"] == "on" and oled_calls == [], (st, oled_calls)

    # 6. Buffyboard still active after stop aborts OLED off
    t[0] += 2.0
    def runner_buffy_active(cmd):
        if cmd[:2] == ["loginctl", "list-sessions"]:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if cmd[:2] == ["systemctl", "show"]:
            return subprocess.CompletedProcess(cmd, 0, "active\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    handle_short_press(st, oled_fn=oled_calls.append, runner=runner_buffy_active,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st["mode"] == "on" and oled_calls == [], (st, oled_calls)

    # 7. Wake UI (buffyboard start rc=1) failure enters fault
    t[0] += 2.0
    st["mode"] = "off"
    def runner_wake_fail(cmd):
        if cmd[:2] == ["systemctl", "start"]:
            return subprocess.CompletedProcess(cmd, 1, "", "failed")
        if cmd[:2] == ["systemctl", "show"]:
            return subprocess.CompletedProcess(cmd, 0, "active\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    handle_short_press(st, oled_fn=oled_calls.append, runner=runner_wake_fail,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st["mode"] == "fault", st

    # 8. Unreadable OLED state on daemon restart -> fault (not on), then recovers
    assert read_oled("/nonexistent/boros_oled/power") == "fault"
    t[0] += 2.0
    st_restart = {"mode": read_oled("/nonexistent/boros_oled/power"), "last_toggle": 0.0}
    oled_calls.clear()
    handle_short_press(st_restart, oled_fn=oled_calls.append, runner=runner_ok,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st_restart["mode"] == "on" and oled_calls == [True], (st_restart, oled_calls)

    # 9. Kernel input_event timestamps: >=3.0s ignored, <3.0s triggers
    t[0] += 2.0
    oled_calls.clear()
    ps = process_key_event(10, 0, EV_KEY, KEY_POWER, 1, None, st_restart,
                           oled_fn=oled_calls.append, runner=runner_ok,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    ps = process_key_event(13, 500000, EV_KEY, KEY_POWER, 0, ps, st_restart,
                           oled_fn=oled_calls.append, runner=runner_ok,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert ps is None and st_restart["mode"] == "on" and oled_calls == []

    ps = process_key_event(20, 0, EV_KEY, KEY_POWER, 1, None, st_restart,
                           oled_fn=oled_calls.append, runner=runner_ok,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    ps = process_key_event(20, 400000, EV_KEY, KEY_POWER, 0, ps, st_restart,
                           oled_fn=oled_calls.append, runner=runner_ok,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert ps is None and st_restart["mode"] == "off" and oled_calls == [False]

    # 10. systemctl show timeout (rc=124) during Buffyboard stop check aborts OLED off
    t[0] += 2.0
    st["mode"] = "on"
    oled_calls.clear()
    def runner_show_timeout(cmd):
        if cmd[:2] == ["loginctl", "list-sessions"]:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if cmd[:2] == ["systemctl", "show"]:
            return subprocess.CompletedProcess(cmd, 124, "", "timeout")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    handle_short_press(st, oled_fn=oled_calls.append, runner=runner_show_timeout,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st["mode"] == "on" and oled_calls == [], (st, oled_calls)

    # 11. getty@tty1 restart failure after stopping Buffyboard restores Buffyboard
    t[0] += 2.0
    started_units = []
    def runner_getty_fail(cmd):
        if cmd[:2] == ["loginctl", "list-sessions"]:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if cmd[:2] == ["systemctl", "show"] and cmd[-1] == "boros-buffyboard.service":
            return subprocess.CompletedProcess(cmd, 0, "inactive\n", "")
        if cmd[:2] == ["systemctl", "show"] and cmd[-1] == "getty@tty1.service":
            return subprocess.CompletedProcess(cmd, 0, "failed\n", "")
        if cmd[:2] == ["systemctl", "restart"] and cmd[2] == "getty@tty1.service":
            return subprocess.CompletedProcess(cmd, 1, "", "failed")
        if cmd[:2] == ["systemctl", "start"]:
            started_units.append(cmd[2])
        return subprocess.CompletedProcess(cmd, 0, "", "")

    handle_short_press(st, oled_fn=oled_calls.append, runner=runner_getty_fail,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st["mode"] == "on" and oled_calls == [] and started_units == ["boros-buffyboard.service"]

    # 12. Skipped systemd Condition* on wake (start rc=0, ActiveState=inactive) -> fault
    t[0] += 2.0
    st["mode"] = "off"
    def runner_cond_skipped(cmd):
        if cmd[:2] == ["systemctl", "show"] and cmd[-1] == "getty@tty1.service":
            return subprocess.CompletedProcess(cmd, 0, "active\n", "")
        if cmd[:2] == ["systemctl", "show"] and cmd[-1] == "boros-buffyboard.service":
            return subprocess.CompletedProcess(cmd, 0, "inactive\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    handle_short_press(st, oled_fn=oled_calls.append, runner=runner_cond_skipped,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st["mode"] == "fault", st

    # 13. getty@tty1 not active (e.g. start-limit-hit) after wake -> fault
    t[0] += 2.0
    st["mode"] = "off"
    def runner_getty_inactive(cmd):
        if cmd[:2] == ["systemctl", "show"] and cmd[-1] == "getty@tty1.service":
            return subprocess.CompletedProcess(cmd, 0, "failed\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    handle_short_press(st, oled_fn=oled_calls.append, runner=runner_getty_inactive,
                       sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert st["mode"] == "fault", st

    # 14. 20 rapid sleep/wake cycles (no tty1 session) -> 0 getty restarts, debounce enforced
    getty_restarts = [0]
    def runner_rapid(cmd):
        if cmd[:2] == ["systemctl", "restart"] and cmd[2] == "getty@tty1.service":
            getty_restarts[0] += 1
        return runner_ok(cmd)

    st_rapid = {"mode": "on", "last_toggle": 0.0}
    oled_calls.clear()
    for _ in range(20):
        t[0] += 2.0
        handle_short_press(st_rapid, oled_fn=oled_calls.append, runner=runner_rapid,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
        # Rapid press within DEBOUNCE_S (1.5s) must be ignored
        t[0] += 0.5
        handle_short_press(st_rapid, oled_fn=oled_calls.append, runner=runner_rapid,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
        assert st_rapid["mode"] == "off"
        t[0] += 2.0
        handle_short_press(st_rapid, oled_fn=oled_calls.append, runner=runner_rapid,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
        assert st_rapid["mode"] == "on"
    assert getty_restarts[0] == 0 and len(oled_calls) == 40, (getty_restarts, len(oled_calls))

    # 15. P04.1: Intentional long press (>=4.0s) triggers orderly systemctl poweroff once
    poweroff_calls = []
    def runner_poweroff(cmd):
        if cmd == ["systemctl", "poweroff"]:
            poweroff_calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return runner_ok(cmd)

    st_lp = {"mode": "on", "last_toggle": 0.0, "shutting_down": False}
    ps = process_key_event(100, 0, EV_KEY, KEY_POWER, 1, None, st_lp,
                           oled_fn=oled_calls.append, runner=runner_poweroff,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    # Duplicate key-down & auto-repeat must not reset press_start
    ps = process_key_event(102, 0, EV_KEY, KEY_POWER, 1, ps, st_lp,
                           oled_fn=oled_calls.append, runner=runner_poweroff,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    ps = process_key_event(103, 0, EV_KEY, KEY_POWER, 2, ps, st_lp,
                           oled_fn=oled_calls.append, runner=runner_poweroff,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert ps == 100.0
    ps = process_key_event(104, 100000, EV_KEY, KEY_POWER, 0, ps, st_lp,
                           oled_fn=oled_calls.append, runner=runner_poweroff,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert ps is None and st_lp["shutting_down"] is True and len(poweroff_calls) == 1

    # 16. P04.1: Continuous hold timeout fires at 4.0s and ignores subsequent release
    poweroff_calls.clear()
    st_hold = {"mode": "on", "last_toggle": 0.0, "shutting_down": False}
    t[0] = 500.0
    assert check_hold_timeout(500.0, st_hold, monotonic_fn=fake_mono, runner=runner_poweroff) is False
    t[0] = 503.9
    assert check_hold_timeout(500.0, st_hold, monotonic_fn=fake_mono, runner=runner_poweroff) is False
    t[0] = 504.0
    assert check_hold_timeout(500.0, st_hold, monotonic_fn=fake_mono, runner=runner_poweroff) is True
    assert len(poweroff_calls) == 1 and st_hold["shutting_down"] is True
    # Subsequent release after shutdown started must be ignored
    ps = process_key_event(504, 500000, EV_KEY, KEY_POWER, 0, 500.0, st_hold,
                           oled_fn=oled_calls.append, runner=runner_poweroff,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert ps is None and len(poweroff_calls) == 1

    # 17. P04.1: Stray release after daemon restart (press_start=None) ignored
    poweroff_calls.clear()
    oled_calls.clear()
    st_stray = {"mode": "on", "last_toggle": 0.0, "shutting_down": False}
    ps = process_key_event(600, 0, EV_KEY, KEY_POWER, 0, None, st_stray,
                           oled_fn=oled_calls.append, runner=runner_poweroff,
                           sleep_fn=fake_sleep, monotonic_fn=fake_mono)
    assert ps is None and oled_calls == [] and poweroff_calls == []

    # 18. P04.1: Failed systemctl poweroff clears shutting_down for retry
    def runner_poweroff_fail(cmd):
        return subprocess.CompletedProcess(cmd, 1, "", "dbus error")
    st_fail = {"mode": "on", "last_toggle": 0.0, "shutting_down": False}
    assert handle_long_press_shutdown(st_fail, runner=runner_poweroff_fail) is False
    assert st_fail["shutting_down"] is False

    print("self-test OK (all 18 state-machine, rapid-cycling & long-press shutdown scenarios passed)")


def main():
    if "--self-test" in sys.argv:
        self_test()
        return

    dev = find_powerkey_dev()
    fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
    sel = selectors.DefaultSelector()
    sel.register(fd, selectors.EVENT_READ)

    state = {"mode": read_oled(), "last_toggle": 0.0, "shutting_down": False}
    press_start = None
    press_start_mono = None
    log(f"watching {dev} (oled={OLED_POWER_PATH}, mode={state['mode']}, shutdown_hold={LONG_PRESS_SHUTDOWN_S}s)")

    while True:
        timeout = SELECT_POLL_S if press_start_mono is not None else 1.0
        events = sel.select(timeout)
        if not events:
            if check_hold_timeout(press_start_mono, state):
                press_start = None
                press_start_mono = None
            continue
        try:
            data = os.read(fd, EVENT_SIZE * 16)
        except BlockingIOError:
            continue

        for off in range(0, len(data) - EVENT_SIZE + 1, EVENT_SIZE):
            sec, usec, etype, code, value = struct.unpack_from(EVENT_FMT, data, off)
            prev = press_start
            press_start = process_key_event(
                sec, usec, etype, code, value, press_start, state
            )
            if prev is None and press_start is not None:
                press_start_mono = time.monotonic()
            elif press_start is None:
                press_start_mono = None


if __name__ == "__main__":
    main()
