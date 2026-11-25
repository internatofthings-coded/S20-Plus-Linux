#!/bin/sh
# NAOMI P09 — Host-side SSH, SCP, and SFTP Compatibility Qualification
# Run on LiBox: sh p09/qualify-ssh-host.sh [<user>@<device-ip>]
set -eu

TARGET="${1:-<user>@<device-ip>}"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== [1/4] Noninteractive SSH (must emit 0 bytes stdout) ==="
OUT="$(ssh -o BatchMode=yes "$TARGET" true)"
[ -z "$OUT" ] || { echo "FAIL: noninteractive SSH emitted output: $OUT"; exit 1; }
echo "PASS: noninteractive SSH clean (0 bytes)"

echo "=== [2/4] Noninteractive SSH command output ==="
HOST_OUT="$(ssh -o BatchMode=yes "$TARGET" hostname)"
echo "Remote hostname: $HOST_OUT"
[ "$HOST_OUT" = "naomi" ] || { echo "FAIL: expected hostname naomi, got $HOST_OUT"; exit 1; }
echo "PASS: remote hostname is naomi"

echo "=== [3/4] SCP round-trip integrity ==="
printf 'naomi-p09-scp-test-%s\n' "$(date +%s)" > "$TMPDIR/src.txt"
SRC_SHA="$(sha256sum "$TMPDIR/src.txt" | awk '{print $1}')"
scp -q -o BatchMode=yes "$TMPDIR/src.txt" "$TARGET:/tmp/naomi-p09-scp.txt"
scp -q -o BatchMode=yes "$TARGET:/tmp/naomi-p09-scp.txt" "$TMPDIR/dst.txt"
DST_SHA="$(sha256sum "$TMPDIR/dst.txt" | awk '{print $1}')"
ssh -o BatchMode=yes "$TARGET" 'rm -f /tmp/naomi-p09-scp.txt'
[ "$SRC_SHA" = "$DST_SHA" ] || { echo "FAIL: SCP checksum mismatch"; exit 1; }
echo "PASS: SCP round-trip checksum verified ($SRC_SHA)"

echo "=== [4/4] SFTP batch transfer integrity ==="
printf 'put %s /tmp/naomi-p09-sftp.txt\nget /tmp/naomi-p09-sftp.txt %s\nrm /tmp/naomi-p09-sftp.txt\n' \
  "$TMPDIR/src.txt" "$TMPDIR/sftp-dst.txt" > "$TMPDIR/sftp.batch"
sftp -q -o BatchMode=yes -b "$TMPDIR/sftp.batch" "$TARGET" >/dev/null
SFTP_SHA="$(sha256sum "$TMPDIR/sftp-dst.txt" | awk '{print $1}')"
[ "$SRC_SHA" = "$SFTP_SHA" ] || { echo "FAIL: SFTP checksum mismatch"; exit 1; }
echo "PASS: SFTP round-trip checksum verified ($SFTP_SHA)"

echo "ALL HOST-SIDE SSH/SCP/SFTP CHECKS PASSED."
