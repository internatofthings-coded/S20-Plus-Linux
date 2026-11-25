#!/usr/bin/env python3
"""NAOMI P09 — Automated Cargo.lock dependency audit (run on LiBox after build)."""

import argparse
import sys
import tempfile
from pathlib import Path

EXPECTED_PINS = {
    "ratatui": "0.29.0",
    "crossterm": "0.28.1",
}

FORBIDDEN_CRATES = {
    "reqwest", "hyper", "tokio", "async-std", "openssl", "rustls",
    "native-tls", "ring", "curl", "serde_json", "ureq",
}


def parse_cargo_lock(text):
    packages = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if line == "[[package]]":
            if current:
                packages.append(current)
            current = {}
            continue
        if current is None or not line or line.startswith("#"):
            continue
        if "=" in line and not line.startswith("["):
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"')
            if k in ("name", "version", "source", "checksum"):
                current[k] = v
    if current:
        packages.append(current)
    return packages


def audit_lockfile(path):
    p = Path(path)
    if not p.is_file():
        return [f"FAIL: lockfile not found: {p}"], {}

    packages = parse_cargo_lock(p.read_text(encoding="utf-8"))
    errors = []
    by_name = {}
    for pkg in packages:
        name = pkg.get("name", "")
        ver = pkg.get("version", "")
        src = pkg.get("source", "")
        by_name.setdefault(name, []).append(ver)

        if name != "naomi-tui":
            if not src.startswith("registry+https://github.com/rust-lang/crates.io-index"):
                errors.append(f"FAIL: non-crates.io source for {name} {ver}: {src!r}")
            if not pkg.get("checksum"):
                errors.append(f"FAIL: missing checksum for {name} {ver}")

        if name in FORBIDDEN_CRATES:
            errors.append(f"FAIL: unexpected network/crypto/async crate in TUI: {name} {ver}")

    for req_name, req_ver in EXPECTED_PINS.items():
        vers = by_name.get(req_name, [])
        if vers != [req_ver]:
            errors.append(f"FAIL: expected {req_name}=={req_ver}, found {vers}")

    dups = {k: v for k, v in by_name.items() if len(v) > 1}
    summary = {
        "total_packages": len(packages),
        "external_packages": sum(1 for x in packages if x.get("name") != "naomi-tui"),
        "duplicate_crates": dups,
    }
    return errors, summary


def self_test():
    good = """
version = 3

[[package]]
name = "naomi-tui"
version = "0.1.0"

[[package]]
name = "ratatui"
version = "0.29.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "abc123"

[[package]]
name = "crossterm"
version = "0.28.1"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "def456"
"""
    bad = good + """
[[package]]
name = "reqwest"
version = "0.12.0"
source = "git+https://example.com/reqwest"
"""
    with tempfile.TemporaryDirectory() as td:
        gp = Path(td) / "good.lock"
        bp = Path(td) / "bad.lock"
        gp.write_text(good, encoding="utf-8")
        bp.write_text(bad, encoding="utf-8")

        errs, summary = audit_lockfile(gp)
        assert not errs, f"expected clean audit, got {errs}"
        assert summary["external_packages"] == 2

        errs_bad, _ = audit_lockfile(bp)
        assert len(errs_bad) >= 3, f"expected >=3 errors for bad lockfile, got {errs_bad}"

    print("audit-cargo-lock self-test OK (2/2 suites passed)")


def main():
    ap = argparse.ArgumentParser(description="Audit NAOMI P07 Cargo.lock")
    ap.add_argument("lockfile", nargs="?", default="p07/Cargo.lock")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return 0

    errors, summary = audit_lockfile(args.lockfile)
    if summary:
        print(
            f"Cargo.lock audit: total={summary['total_packages']} "
            f"external={summary['external_packages']} "
            f"duplicates={len(summary['duplicate_crates'])}"
        )
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print("PASS: Cargo.lock dependency audit clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
