#!/usr/bin/env bash
# Inside Debian (proot on Android, or any Debian/Ubuntu Linux): install everything the app needs.
# Called by android/install.sh; safe to run again (it skips what is already there).
#   bash android/setup-debian.sh [--speech] [--assets] [--mixkit]
set -euo pipefail
APP="$(cd "$(dirname "$0")/.." && pwd)"
WS="$APP/workspace"
SPEECH=0; ASSETS=0; MIXKIT=0
for a in "$@"; do case "$a" in --speech) SPEECH=1;; --assets) ASSETS=1;; --mixkit) MIXKIT=1;; esac; done
HF_VERSION="$(grep -oE 'HyperframesVersion = "[0-9.]+"' "$APP/app/setup.ps1" | grep -oE '[0-9.]+' || echo 0.9.43)"
DRIVE="https://drive.google.com/drive/folders/14AIdAfaVGiNaJlnlpApHV9dwMUfGM-5N"
PHONE="/sdcard/Movies/AI Video Editor"
say() { printf '\n\033[1;36m-- %s\033[0m\n' "$1"; }
export DEBIAN_FRONTEND=noninteractive

say "System packages: Python, ffmpeg, Chromium, fonts"
apt-get update -qq
apt-get install -y -qq python3 ffmpeg chromium git curl ca-certificates xz-utils unzip procps \
  fonts-noto-core fonts-noto-color-emoji fonts-dejavu-core >/dev/null

say "Node.js 22 (HyperFrames needs 22 or newer; checked against nodejs.org's SHA-256 list)"
if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 22 ]; then
  case "$(uname -m)" in aarch64|arm64) NA=arm64;; x86_64) NA=x64;; *) echo "unsupported CPU $(uname -m)"; exit 1;; esac
  BASE="https://nodejs.org/dist/latest-v22.x"
  FILE="$(curl -fsSL "$BASE/SHASUMS256.txt" | grep -oE "node-v22[0-9.]+-linux-$NA\.tar\.xz" | head -1)"
  curl -fsSL "$BASE/$FILE" -o "/tmp/$FILE"
  (cd /tmp && curl -fsSL "$BASE/SHASUMS256.txt" | grep " $FILE\$" | sha256sum -c -)
  tar -xJf "/tmp/$FILE" -C /usr/local --strip-components=1 && rm -f "/tmp/$FILE"
fi
node --version

say "Claude Code, Codex and HyperFrames (official Linux builds)"
npm install -g --no-fund --no-audit @anthropic-ai/claude-code @openai/codex >/dev/null
claude --version || echo "  (claude did not start; run: aive doctor)"
codex --version || echo "  (codex did not start; run: aive doctor)"

say "Environment for the app"
cat > /etc/profile.d/ai-video-editor.sh <<EOF
export RR_PLATFORM=android
export HYPERFRAMES_BROWSER_PATH=/usr/bin/chromium
export PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
export HYPERFRAMES_CHROME_SANDBOX=0
export PYTHONUTF8=1
EOF
# shellcheck disable=SC1091
. /etc/profile.d/ai-video-editor.sh
if [ -f "$HOME/whisper.cpp/build/bin/whisper-cli" ]; then echo "export HYPERFRAMES_WHISPER_PATH=$HOME/whisper.cpp/build/bin/whisper-cli" >> /etc/profile.d/ai-video-editor.sh; fi

say "Video skills for Claude and Codex (HyperFrames $HF_VERSION)"
(cd "$WS" && npx --yes "hyperframes@$HF_VERSION" skills update) || echo "  skills update failed; run it later with: aive update"

say "Phone folders"
mkdir -p "$WS/videos" "$WS/projects" "$WS/assets" "$WS/review"
if [ -d /sdcard ] || [ -d /storage/emulated/0 ]; then
  [ -d /sdcard ] || ln -s /storage/emulated/0 /sdcard
  mkdir -p "$PHONE/Finished"
  [ -e "$WS/videos/Phone" ] || ln -s "$PHONE" "$WS/videos/Phone"
  python3 - "$APP" "$PHONE/Finished" <<'EOF'
import json, sys, pathlib
app, out = pathlib.Path(sys.argv[1]), sys.argv[2]
d = json.loads((app / "app/data/settings.default.json").read_text(encoding="utf-8"))
sp = app / "settings.json"
cur = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
cur.setdefault("export_dir", out)
sp.write_text(json.dumps({**d, **cur}, indent=2) + "\n", encoding="utf-8")
EOF
  echo "  videos: $PHONE  (finished videos are copied to its Finished folder)"
fi

if [ "$SPEECH" = 1 ]; then
  say "Speech: whisper.cpp (built for this CPU, about 10 minutes on a phone) + the small model"
  apt-get install -y -qq build-essential cmake >/dev/null
  if [ ! -x "$HOME/whisper.cpp/build/bin/whisper-cli" ]; then
    rm -rf "$HOME/whisper.cpp"; git clone --depth 1 https://github.com/ggml-org/whisper.cpp "$HOME/whisper.cpp"
    cmake -S "$HOME/whisper.cpp" -B "$HOME/whisper.cpp/build" -DCMAKE_BUILD_TYPE=Release -DWHISPER_BUILD_TESTS=OFF >/dev/null
    cmake --build "$HOME/whisper.cpp/build" -j "$(nproc)" --target whisper-cli whisper-server >/dev/null
  fi
  M="$HOME/.cache/hyperframes/whisper/models"; mkdir -p "$M"
  if [ ! -f "$M/ggml-small.bin" ]; then
    curl -fL "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin" -o "$M/ggml-small.bin.part"
    echo "1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b  $M/ggml-small.bin.part" | sha256sum -c - \
      && mv "$M/ggml-small.bin.part" "$M/ggml-small.bin"
  fi
  grep -q HYPERFRAMES_WHISPER_PATH /etc/profile.d/ai-video-editor.sh || \
    echo "export HYPERFRAMES_WHISPER_PATH=$HOME/whisper.cpp/build/bin/whisper-cli" >> /etc/profile.d/ai-video-editor.sh
fi

if [ "$ASSETS" = 1 ]; then
  say "Asset library: the shareable pack from Google Drive (0.7 GB download, 1.1 GB unpacked)"
  apt-get install -y -qq python3-venv >/dev/null
  python3 -m venv "$HOME/.venv-gdown" && "$HOME/.venv-gdown/bin/pip" -q install gdown
  "$HOME/.venv-gdown/bin/gdown" --folder "$DRIVE" -O /tmp/rr-pack
  for z in /tmp/rr-pack/*.zip; do unzip -q -o "$z" -d "$WS/assets"; done
  rm -rf /tmp/rr-pack
fi
if [ "$MIXKIT" = 1 ]; then
  say "Mixkit music, sound effects and footage (2.7 GB)"
  python3 "$APP/app/tools/fetch_mixkit_assets.py"
fi

say "Learning the asset library"
python3 "$APP/app/tools/learn_assets.py" || true
RR_PLATFORM=android python3 "$APP/app/gpu.py" --force || true
echo
echo "Setup finished."
