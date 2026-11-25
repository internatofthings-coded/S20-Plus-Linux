# BOROS Bundle B — Interactive Login TUI Hook (/etc/profile.d/99-boros-tui.sh)
# Runs alphabetically after 99-boros-motd.sh so Bundle A MOTD is always preserved.
# Strictly gated to interactive TTY logins; never affects SCP/SFTP/noninteractive SSH/Ansible.

case "$-" in
  *i*) ;;
  *) return 0 2>/dev/null || exit 0 ;;
esac

# Must be an interactive TTY on both stdin and stdout.
[ -t 0 ] && [ -t 1 ] || return 0 2>/dev/null || exit 0

# Direct shell bypasses & recursion guard.
[ -z "${NAOMI_NO_TUI:-}" ] || return 0 2>/dev/null || exit 0
[ -z "${NAOMI_TUI_ACTIVE:-}" ] || return 0 2>/dev/null || exit 0
[ ! -f "${HOME:-/nonexistent}/.naomi-no-tui" ] || return 0 2>/dev/null || exit 0
[ ! -f /etc/boros/no-tui ] || return 0 2>/dev/null || exit 0

# Load auto-launch configuration (default: disabled until owner enables AUTO_LAUNCH=1).
NAOMI_TUI_CONF="${NAOMI_TUI_CONF:-/etc/boros/tui.conf}"
AUTO_LAUNCH=0
if [ -r "$NAOMI_TUI_CONF" ]; then
  # Parse only AUTO_LAUNCH=0|1 without executing arbitrary shell code.
  case "$(grep -E '^[[:space:]]*AUTO_LAUNCH=' "$NAOMI_TUI_CONF" | tail -n 1 | cut -d= -f2 | tr -d '[:space:]')" in
    1|true|yes) AUTO_LAUNCH=1 ;;
    *) AUTO_LAUNCH=0 ;;
  esac
fi

[ "$AUTO_LAUNCH" = "1" ] || return 0 2>/dev/null || exit 0

NAOMI_TUI_LAUNCHER="${NAOMI_TUI_LAUNCHER:-/usr/local/bin/naomi-tui-launch}"
[ -x "$NAOMI_TUI_LAUNCHER" ] || return 0 2>/dev/null || exit 0

# Launch as a child process; never terminate the user's shell on exit or crash.
"$NAOMI_TUI_LAUNCHER" || true
