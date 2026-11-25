# BOROS Bundle A — Interactive Login MOTD Hook
# Strictly gated to interactive TTY sessions; never runs for SCP/SFTP/noninteractive SSH.
case "$-" in
  *i*) ;;
  *) return 0 2>/dev/null || exit 0 ;;
esac

[ -t 0 ] && [ -t 1 ] || return 0 2>/dev/null || exit 0
[ -z "${BOROS_MOTD_SHOWN:-}" ] || return 0 2>/dev/null || exit 0
[ -x /usr/local/bin/boros-motd ] || return 0 2>/dev/null || exit 0

BOROS_MOTD_SHOWN=1
/usr/local/bin/boros-motd 2>/dev/null || true
