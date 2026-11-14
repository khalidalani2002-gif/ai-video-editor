# AI Video Editor on Android

The same editor runs on an Android phone, inside the free **Termux** app. It is **2D only**: no Blender or 3D. Everything
else works: editing notes, Make a video, HyperFrames motion graphics, captions, colour, Quick preview + Render final,
Claude or Codex, the asset library and updates.

How it works: Termux runs a small **Debian Linux** (through `proot-distro`, no root needed). Debian has the official Linux
builds of Claude Code, Codex, Node.js 22, ffmpeg and Chromium, so nothing is emulated. The editor runs there as a local
server, and you use it in the phone's browser at `http://127.0.0.1:8770`.

## Install (about 2.5 GB; 10 to 20 minutes)

1. Install **Termux** from [F-Droid](https://f-droid.org/packages/com.termux/) or its
   [GitHub releases](https://github.com/termux/termux-app/releases). The old Play Store build does not work.
2. Open Termux and paste:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/khalidalani2002-gif/ai-video-editor/main/android/install.sh | bash
   ```

   Add the extras you want: `| bash -s -- --speech --assets` (`--speech`: spoken notes and transcripts, +0.5 GB, builds
   for about 10 minutes; `--assets`: the shareable asset pack, +1.1 GB; `--mixkit`: Mixkit music, sound effects and
   footage, +2.7 GB). Allow the storage permission when Android asks.
3. `aive login`: sign in to Claude and/or Codex. Each sign-in shows a link: open it, sign in, and come back.
   (Or on a PC run `claude setup-token` and paste the token with option 2.)
4. `aive start`: the editor opens in your browser. Add it to the home screen from the browser menu if you like.

Set **Settings > Apps > Termux > Battery > Unrestricted**, otherwise Android may stop long renders when the screen is off.
`aive start` also keeps the phone awake (Termux's wake lock) until `aive stop`.

## Your videos

- Put videos in **Movies/AI Video Editor** on the phone: they appear in the editor under **Phone**. New versions are saved
  next to them, so they show up in the gallery.
- Or press **Add videos** / **Choose files** in the editor to pick files.
- Finished videos (made videos, final renders, approved edits) are also copied to **Movies/AI Video Editor/Finished**.
- On the phone, "deleted" files go to `workspace/review/trash/` inside the app (there is no Recycle Bin).

## Commands

| | |
|---|---|
| `aive start` / `aive stop` | start or stop the editor |
| `aive login` | Claude and Codex sign-in, test, sign-out |
| `aive update` | get the newest version (the in-app **Update** button works too) |
| `aive logs` | the server log, if something goes wrong |
| `aive doctor` | check the tools |
| `aive shell` | a shell inside Debian, in the app folder |

## Speed (compared with a desktop PC with a GPU)

| | Phone |
|---|---|
| The AI's thinking (Claude / Codex) | the same: it runs on their servers |
| Cuts, colour, captions (ffmpeg) | about 1.5 to 2 times slower (the phone heats up on long encodes) |
| Quick preview drafts | fast; use them, and press Render final while charging |
| Speech (small model, CPU) | about 30 to 90 s per minute of video |
| HyperFrames motion graphics | about 3 to 5 times slower (Chromium renders on the CPU) |
| 3D | not on Android |

## Uninstall

`aive stop`, then `proot-distro remove debian` and `rm $PREFIX/bin/aive`. The videos in Movies/AI Video Editor stay.
