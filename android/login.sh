#!/usr/bin/env bash
# Sign in to Claude and/or Codex on this phone (run with:  aive login).
# Same choices as "Claude Login.bat" and "Codex Login.bat" on Windows. Sign-ins stay in Debian's /root, never in the app.
# Keys and tokens are typed hidden and never printed or written to the app folder.
APP="$(cd "$(dirname "$0")/.." && pwd)"
TOKFILE=/etc/profile.d/claude-token.sh

status() {
  echo
  if command -v claude >/dev/null; then
    printf '  Claude: '; claude auth status 2>/dev/null | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('unknown'); sys.exit()
print(('signed in' + (' as ' + d['email'] if d.get('email') else '') + ' (' + str(d.get('authMethod','')) + ')') if d.get('loggedIn') else 'not signed in')"
  else echo '  Claude: not installed (bash android/setup-debian.sh)'; fi
  if command -v codex >/dev/null; then
    printf '  Codex:  '; python3 "$APP/app/tools/codex_path.py" --status 2>/dev/null | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print('unknown'); sys.exit()
print(('signed in' + (' as ' + d['email'] if d.get('email') else '') + ' (' + str(d.get('method') or '') + ')') if d.get('signed_in') else 'not signed in')"
  else echo '  Codex:  not installed (bash android/setup-debian.sh)'; fi
}

while true; do
  status
  cat <<'EOT'

  Claude                                   Codex
  [1] Sign in (opens a link)               [5] Sign in with ChatGPT (opens a link)
  [2] Paste a sign-in token                [6] Sign in with an API key
  [3] Test                                 [7] Test
  [4] Sign out                             [8] Sign out
  [0] Exit (or just Enter)
EOT
  read -r -p "  Choose: " CH
  case "$CH" in
    1) claude auth login || echo "  Tip: on a PC run 'claude setup-token' and use option [2]." ;;
    2) read -r -s -p "  Paste the token from 'claude setup-token' (hidden): " TOK; echo
       if [ -n "$TOK" ]; then
         umask 077; printf 'export CLAUDE_CODE_OAUTH_TOKEN=%q\n' "$TOK" > "$TOKFILE"; unset TOK
         echo "  Saved for this phone's Debian (only root can read it)."; fi ;;
    3) [ -f "$TOKFILE" ] && . "$TOKFILE"
       R=$(echo 'Reply with exactly: ok' | timeout 120 claude -p --model claude-opus-5-5 2>&1 | tail -1)
       case "$R" in *ok*|*OK*) echo "  OK. The editor can use Claude.";; *) echo "  Test failed: ${R:0:200}";; esac ;;
    4) claude auth logout >/dev/null 2>&1; rm -f "$TOKFILE"; echo "  Signed out of Claude." ;;
    5) echo "  A link opens (or copy it into the browser). Finish the sign-in there, then come back."
       codex login ;;
    6) read -r -s -p "  Paste the OpenAI API key (hidden): " KEY; echo
       if [ -n "$KEY" ]; then
         if printf '%s' "$KEY" | codex login --with-api-key >/dev/null 2>&1; then echo "  Signed in with an API key."
         else echo "  Sign-in failed. Check the key."; fi
         unset KEY; fi ;;
    7) M=$(python3 -c "import json;print(json.load(open('$APP/settings.json')).get('codex_model','gpt-6.1-sol'))" 2>/dev/null || echo gpt-6.1-sol)
       R=$(echo 'Reply with exactly: ok' | timeout 180 codex exec --skip-git-repo-check -m "$M" -c model_reasoning_effort=low -s read-only - 2>&1 | tail -3)
       case "$R" in *ok*|*OK*) echo "  OK. The editor can use Codex ($M).";; *) echo "  Test failed: ${R:0:300}";; esac ;;
    8) codex logout >/dev/null 2>&1; echo "  Signed out of Codex." ;;
    *) exit 0 ;;
  esac
done
