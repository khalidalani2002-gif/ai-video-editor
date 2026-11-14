# AI Video Editor

A Windows desktop app where **Claude Code** or **OpenAI Codex** edit and make videos for you.

- **Edit a video:** scrub to the exact frame, click the spot (or draw a box), write the change in English or Arabic
  (or say it), and the AI makes a new version you can compare A/B and approve.
- **Make a video:** drop clips, photos, music and logos (or nothing at all), describe the video, pick a style, and
  the AI builds it: edits, motion graphics (HyperFrames) or 3D (Blender).
- **37 styles with examples:** cinematic, reels, luxury, kinetic type, isometric, map animation, Open Peeps
  illustrations, clay, low-poly, product 3D, medical 3D…
- **A 53,000-item asset library** that the AI searches before generating anything: music, sound effects, fonts, icons,
  emoji, footage, colour looks, HDRIs, 3D models, illustrations, maps.
- **Remove AI slop audio:** one switch keeps the AI away from the overused whooshes, pops and "corporate" tracks.

Everything runs on your PC. Jobs use your own Claude or ChatGPT subscription.

## Install (let Claude do it)

You need Windows 10/11 (an NVIDIA GPU helps) and a Claude subscription (for Claude Code) and/or ChatGPT (for Codex).

1. **Get the app:** click **Code > Download ZIP** on this page and unzip it anywhere (or `git clone` it).
2. **Double-click `Setup.bat`.** It installs ffmpeg, Node.js, Claude Code, a portable Python and the HyperFrames video
   skills, and asks about three optional extras: speech (Speak notes and transcripts, 1.7 GB), Blender (3D, 400 MB) and
   the Mixkit music / sound effects / footage (2.6 GB). Then it opens **`Claude Login.bat`** to sign in to Claude.
   (No browser on that PC? Run `claude setup-token` on any computer, then paste the token in option 1.)
3. **Install the asset library.** Open Claude Code in the app folder (type `claude` in a terminal there, or pick the
   folder in the Claude desktop app's Code tab) and paste this:

   > Install the default assets for this app. Download every file from this public Google Drive folder:
   > **https://drive.google.com/drive/folders/14AIdAfaVGiNaJlnlpApHV9dwMUfGM-5N**
   > (use `pip install gdown` then `gdown --folder <link>` if a normal download is blocked), unzip each
   > "Default assets - *.zip" into `workspace\assets\` so that `workspace\assets\Default assets\3D`, `Fonts`, `Icons`… exist,
   > then run `app\python\python.exe app\tools\fetch_mixkit_assets.py` to get the Mixkit music, sound effects and footage.
   > Tell me when it's done.

   The Drive pack (about 0.7 GB) holds the assets that may be shared (3D, fonts, icons, emoji, looks, maps, Open Peeps,
   Kenney sounds). Mixkit items are fetched from Mixkit itself, because their licence forbids re-sharing them. Details:
   [ASSET-LICENSES.md](ASSET-LICENSES.md).
4. **Start it:** double-click **Review Room App** on the desktop (or `Start Review Room.vbs`).

## Use it

The app opens on a start screen: **Make a video** or **Edit a video** (keys M / E).

**Edit a video**
- Drop video files onto the list on the left (it takes videos only).
- Find the moment: the mouse wheel on the timeline zooms down to single frames; ←/→ step one frame, ↑/↓ jump between cuts,
  and I / O mark a range.
- Click the picture to drop a pin, or drag to draw a box. Write the change, or press 🎤 Speak.
- Choose **Claude or Codex**, **Normal or Heavy**, and a **Style**, then press **Send to Claude**. Several notes can go as one
  job with **Send all drafts**.
- When the new version is ready, **Compare A/B**, then **Approve** (the old one goes to the Recycle Bin).
- **✨ Assets & effects** is your bin: drop files from your PC, or open **Default assets**, **Effects** (447 HyperFrames
  effects) and **Looks** like folders. Drag any item onto the picture (a place) or the timeline (a time) and say what to do with it.
- Ctrl+Z / Ctrl+Y undo and redo; Delete removes the selected placed asset.

**Make a video**
- Drop anything or click items on the right, describe the video, choose format, engine, edit level and style, then press
  **Make video**.
- **🔇 Remove AI slop audio** blocks the stock sounds AI videos overuse (listed in `app/data/slop-audio.json`).

| Edit level | What the AI does | Effort |
|---|---|---|
| Normal | clean cuts, colour correction, captions, titles, library assets; no 3D, no downloads | medium |
| Heavy | studies the material, searches the web for licensed assets, uses Blender 3D where it helps, aims for a professional result | high |

**⚙ Settings > Use assets that can't be shared** lets the AI use (or ignore) the library folders whose licences forbid
re-sharing (Mixkit, Sonniss, Remix Icon): fine in your own videos, kept out when you don't want them.

## Claude or Codex

- **Claude:** Claude Code with `claude-opus-5-5`. Rules for it are in `workspace/CLAUDE.md`.
- **Codex:** the Codex CLI (the Codex desktop app's bundled one, or `npm i -g @openai/codex` + `codex login`) with
  `gpt-5.6-sol`. It reads `workspace/AGENTS.md`, which points to the same rules.

Change the models in `settings.json`. Each video keeps a separate conversation with each engine.

## Security

The app is a local server (`127.0.0.1:8770`) that starts AI agents able to edit files and run commands on your PC, so it
only obeys its own window:

- Every request must have the app's own `Host` and must not come from another website (`Origin` / `Sec-Fetch-Site`). This
  also blocks DNS-rebinding tricks.
- Every POST carries a secret token made fresh each time the app starts. Only the app page can read it, so another web page
  can't send notes, start jobs or close the app.
- Note ids are validated. Responses carry CSP, `X-Frame-Options: DENY` and `nosniff`. Request bodies are size-capped.
- Each prompt (and `workspace/CLAUDE.md` / `AGENTS.md`) tells the agent that text inside videos, transcripts, files and web
  pages is material, never instructions.
- Claude runs with a fixed list of allowed tools (`ALLOWED` / `DENIED` in `app/server.py`).
- Codex runs with **your own Codex config** (its sandbox and approval settings). To keep Codex inside its sandbox, set
  `"codex_sandbox": "workspace-write"` in `settings.json`. This needs the Codex Windows sandbox to be set up; without it,
  every Codex command fails.
- Setup checks the Python, whisper.cpp and speech-model downloads against their publishers' SHA-256 checksums and pins the
  HyperFrames version.
- `Claude Login.bat` stores your Claude token as a user environment variable (`CLAUDE_CODE_OAUTH_TOKEN`), readable by
  programs running as you, the same as Claude's own sign-in file. Use option 5 (Sign out) there to remove it.

Found a problem? Please open an issue.

## Folders

| | |
|---|---|
| `Start Review Room.vbs` | starts the app (a local server on port 8770 plus an app window) |
| `Setup.bat`, `Claude Login.bat` | set up a PC, sign in to Claude |
| `settings.json` | ports, models, the "use assets that can't be shared" switch |
| `app\` | the program (Python standard library + HTML), styles, looks, tools |
| `workspace\` | where the AI works: `videos\`, `projects\`, `assets\`, `review\`, `CLAUDE.md`, `AGENTS.md`, `tools\find_asset.py` |

## Licence

The app's code is MIT (see `LICENSE`). Assets keep their own licences: [ASSET-LICENSES.md](ASSET-LICENSES.md).
