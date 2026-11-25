#!/bin/sh
# Build, unit-test, cross-compile (ARM64), and measure naomi-tui on LiBox.
# Requires: rustup + aarch64-unknown-linux-gnu target + aarch64-linux-gnu-gcc
set -eu

cd "$(dirname "$0")"

echo "=== 1. Run host unit tests (navigation, theme, responsive layouts) ==="
cargo test

echo "=== 2. Cross-compile release binary for ARM64 (aarch64-unknown-linux-gnu) ==="
cargo build --release --target aarch64-unknown-linux-gnu

BIN="target/aarch64-unknown-linux-gnu/release/naomi-tui"
echo "=== 3. Verify ELF architecture & size ==="
file "$BIN"
ls -lh "$BIN"
sha256sum "$BIN"

echo "=== 4. Quick QEMU ARM64 smoke test (--version) ==="
if command -v qemu-aarch64-static >/dev/null 2>&1; then
  qemu-aarch64-static "$BIN" --version
else
  echo "SKIP: qemu-aarch64-static not installed"
fi

echo "Build and ARM64 verification complete: $BIN"
