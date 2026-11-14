#!/data/data/com.termux/files/usr/bin/bash
# AI Video Editor for Android: one-time install, run inside the Termux app.
#
#   curl -fsSL https://raw.githubusercontent.com/khalidalani2002-gif/ai-video-editor/main/android/install.sh | bash
#   (add  -s -- --speech  for spoken notes and transcripts,  --assets  for the shareable asset pack,  --mixkit  for Mixkit)
#
# What it does: Termux gets proot-distro and a Debian (arm64) Linux; Debian gets Python, Node 22, ffmpeg, Chromium,
# Claude Code, Codex and HyperFrames (official Linux builds); the app lives in Debian at /root/ai-video-editor.
# Then the command  aive  starts it (aive start | stop | login | update | logs | shell | doctor).
# 2D only on Android: no Blender / 3D.
# Everything runs inside main(): with "curl | bash" the script itself arrives on stdin, and bash must read all of it
# before anything below can read stdin (Debian's setup would otherwise swallow the rest of this file).
main() {
set -euo pipefail
REPO="${AIVE_REPO:-https://github.com/khalidalani2002-gif/ai-video-editor}"
ARGS="$*"
say() { printf '\n\033[1;33m== %s\033[0m\n' "$1"; }

if [ -z "${PREFIX:-}" ] || [ ! -d "/data/data/com.termux" ]; then
  echo "Run this inside the Termux app on Android (from F-Droid or GitHub, not the old Play Store build)."; exit 1
fi

say "1/5 Termux packages"
yes | pkg update -y >/dev/null 2>&1 || true
PKGS="proot-distro git curl termux-tools procps"
if ! pkg install -y $PKGS </dev/null; then
  # a random mirror can be down or rate-limited: fall back to Termux's official server and try again
  echo "  The package mirror failed; switching to packages.termux.dev and retrying."
  echo "deb https://packages-cf.termux.dev/apt/termux-main stable main" > "$PREFIX/etc/apt/sources.list"
  rm -rf "$PREFIX/etc/termux/chosen_mirrors" 2>/dev/null || true
  apt-get update </dev/null && pkg install -y $PKGS </dev/null
fi

say "2/5 Phone storage (allow the permission prompt)"
if [ ! -d "$HOME/storage/shared" ]; then termux-setup-storage || true; sleep 4; fi
mkdir -p "/storage/emulated/0/Movies/AI Video Editor/Finished" 2>/dev/null || true

say "3/5 Debian Linux (about 300 MB; it holds the app and its tools)"
if ! proot-distro login debian -- true </dev/null 2>/dev/null; then proot-distro install debian </dev/null; fi

say "4/5 The app and its tools inside Debian (10-20 minutes the first time)"
proot-distro login debian --shared-tmp -- bash -c "
  set -e
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq && apt-get install -y -qq git ca-certificates curl >/dev/null
  if [ -d /root/ai-video-editor/.git ]; then git -C /root/ai-video-editor pull --ff-only || true
  else git clone --depth 1 $REPO /root/ai-video-editor; fi
  bash /root/ai-video-editor/android/setup-debian.sh $ARGS
" </dev/null

say "5/5 The 'aive' command and a home-screen shortcut"
SCRIPT_DIR="$PREFIX/share/ai-video-editor"; mkdir -p "$SCRIPT_DIR"
proot-distro login debian -- cat /root/ai-video-editor/android/aive </dev/null > "$PREFIX/bin/aive"
chmod +x "$PREFIX/bin/aive"
mkdir -p "$HOME/.shortcuts"
printf '#!/data/data/com.termux/files/usr/bin/bash\naive start\n' > "$HOME/.shortcuts/AI Video Editor"
chmod +x "$HOME/.shortcuts/AI Video Editor"

cat <<'EOT'

Done. Next:
  1. aive login     sign in to Claude and/or Codex (once)
  2. aive start     start the editor; it opens in your browser at http://127.0.0.1:8770
Tips:
  - Settings > Apps > Termux > Battery: Unrestricted, so long renders are not stopped.
  - Put videos in  Movies/AI Video Editor  on the phone; finished videos are copied to its "Finished" folder.
  - Optional: install Termux:Widget to start the editor from a home-screen widget.
EOT
}
main "$@"
