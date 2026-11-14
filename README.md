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
- **⚡ Quick preview:** the AI makes the edit and renders only a fast draft; press **Render final** when you like it.
- **Learns your assets:** when assets are installed or added, the app indexes them and writes a guide the AI reads.
- **NVIDIA, AMD and Intel GPUs:** it tests what works on your PC and tells the AI to use it.
- **Updates itself:** when a new version is on GitHub, **Let Claude update** installs it without touching your work.

Everything runs on your PC. Jobs use your own Claude or ChatGPT subscription.

## Install (let Claude do it)

You need Windows 10/11 (an NVIDIA, AMD or Intel GPU helps) and a Claude subscription (for Claude Code) and/or ChatGPT (for Codex).

1. **Get the app:** click **Code > Download ZIP** on this page and unzip it anywhere (or `git clone` it).
2. **Double-click `Setup.bat`.** It installs ffmpeg, Node.js, Claude Code, a portable Python and the HyperFrames video
   skills, and asks about three optional extras: speech (Speak notes and transcripts, 1.7 GB), Blender (3D, 400 MB) and
   the Mixkit music / sound effects / footage (2.6 GB). Setup also offers the Codex CLI if it is missing, then opens **`Claude Login.bat`** and **`Codex Login.bat`**.
   Connect Claude, Codex or both; press Enter or 0 to skip either menu.
   (No browser on that PC? Run `claude setup-token` on any computer, then paste the token in option 1.)
3. **Install the asset library.** Open Claude Code in the app folder (type `claude` in a terminal there, or pick the
   folder in the Claude desktop app's Code tab) and paste this:

   > Install the default assets for this app. Download every file from this public Google Drive folder:
   > **https://drive.google.com/drive/folders/14AIdAfaVGiNaJlnlpApHV9dwMUfGM-5N**
   > (use `pip install gdown` then `gdown --folder <link>` if a normal download is blocked), unzip each
   > "Default assets - *.zip" into `workspace\assets\` so that `workspace\assets\Default assets\3D`, `Fonts`, `Icons`… exist,
   > then run `app\python\python.exe app\tools\fetch_mixkit_assets.py` to get the Mixkit music, sound effects and footage.
   > Tell me when it's done.

   The Drive pack is 0.7 GB to download and **1.1 GB unzipped** (46,000 files); the Mixkit items add **2.7 GB**
   (3,330 files), so plan for about **3.8 GB**. It holds the assets that may be shared (3D, fonts, icons, emoji, looks, maps, Open Peeps,
   Kenney sounds). Mixkit items are fetched from Mixkit itself, because their licence forbids re-sharing them. Details:
   [ASSET-LICENSES.md](ASSET-LICENSES.md).
4. **Start it:** double-click **Review Room App** on the desktop (or `Start Review Room.vbs`). The app notices the new
   assets, learns them (`workspace\ASSETS.md`) and offers to let Claude study them (`workspace\ASSET-NOTES.md`).

## Use it

The app opens on a start screen: **Make a video** or **Edit a video** (keys M / E).

**Edit a video**
- Drop video files onto the list on the left (it takes videos only).
- Find the moment: the mouse wheel on the timeline zooms down to single frames; ←/→ step one frame, ↑/↓ jump between cuts,
  and I / O mark a range.
- Click the picture to drop a pin, or drag to draw a box. Write the change, or press 🎤 Speak.
- Choose **Claude or Codex**, **Normal or Heavy**, and a **Style**, then press **Send to Claude**. Several notes can go as one
  job with **Send all drafts**.
- With **⚡ Quick preview: on** (the default) the AI renders a fast draft, `<name> (rev N preview).mp4`, with the same
  timing, so you can **Compare A/B** quickly and keep sending notes. When it looks right, press **🎬 Render final**: the app
  renders the full-quality version from the recipe the AI saved, with no extra AI job, and sends the preview to the
  Recycle Bin. Turn Quick preview off to get a full render after every edit.
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

## Updates

The version is in `VERSION` (shown next to the title). The app checks GitHub every few hours (or **⚙ Settings > Check for
updates**). When there is a newer version, **⬆ Update** shows what is new; **Let Claude update** starts one AI job that runs
`app\tools\update.py`:

- it downloads the new version and replaces only the app's own files, after copying each one to `backups\<version>-<time>\`;
- it never writes your videos, projects, assets, notes or `settings.json` (new settings are only added), and checks that
  they are unchanged afterwards. If anything fails it rolls back by itself;
- an app file you edited yourself is kept, and the AI merges the new version (`*.update-new`) into it by hand;
- a `git clone` without local changes updates with `git pull`.

When it finishes, the app closes; open it again to use the new version. To undo: `app\python\python.exe app\tools\update.py --rollback`.

**Updating from 1.0.0** (it has no update button yet): open Claude Code in the app folder and paste:

> Update this app from https://github.com/khalidalani2002-gif/ai-video-editor to the newest version. Download the repo as a
> ZIP, copy its files over this folder, but never touch `workspace\videos`, `workspace\projects`, `workspace\assets`,
> `workspace\review` or `app\python`, and keep my `settings.json` values. Then restart the app.

## GPU: NVIDIA, AMD and Intel

`app\gpu.py` (run by Setup, and by the app at start) tests what this PC can really do and puts it in every job:

| | NVIDIA | AMD | Intel |
|---|---|---|---|
| Fast video encoding (ffmpeg) | NVENC `h264_nvenc` | AMF `h264_amf` | Quick Sync `h264_qsv` |
| Blender Cycles | CUDA (OptiX on RTX) | HIP (Radeon RX 5000 and newer) | oneAPI (Arc) |
| Speech (whisper.cpp) | CUDA build | fast CPU build (OpenBLAS) | fast CPU build (OpenBLAS) |
| HyperFrames (Chrome) | GPU | GPU | GPU |

Each encoder is tested by encoding a few frames, and Blender is asked which devices it sees. If a GPU's encoder fails
(usually an old driver), the app uses the CPU encoder and **⚙ Settings > GPU** shows why, with the vendor's driver page. Install
or update graphics drivers yourself from NVIDIA, AMD or Intel; the app never installs drivers.

## Claude or Codex

- **Claude:** Claude Code with `claude-opus-5-5`. Rules for it are in `workspace/CLAUDE.md`.
- **Codex:** open `Codex Login.bat` to sign in with ChatGPT or an API key, test the connection, or install / update the CLI.
  The app uses the newest installed CLI (your `codex_path`, the Codex desktop app, sandbox-bin or PATH / npm), checked
  every ten minutes. It uses `gpt-6.1-sol`, with one retry on `gpt-5.6-sol` if the model is not supported.
  It reads `workspace/AGENTS.md`, which points to the same rules.

The header and **⚙ Settings > AI engines** show which engines are signed in, their models, and the Codex account and
CLI version. Connect either engine or both and pick one for each job. The app notices a new sign-in when it opens
or when you send a job. Normal edits use medium effort; heavy edits use high effort.

Change the models (`model`, `codex_model`, `codex_fallback_model`) in `settings.json` (your copy; the defaults are in `app\data\settings.default.json`). Each video keeps a separate conversation with each engine.

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
| `Setup.bat`, `Claude Login.bat`, `Codex Login.bat` | set up a PC, sign in to Claude and / or Codex |
| `VERSION`, `CHANGELOG.md` | the app version and what changed |
| `settings.json` | your settings: ports, models, the "use assets that can't be shared" switch (made on first start) |
| `backups\` | app files replaced by updates |
| `app\` | the program (Python standard library + HTML), styles, looks, tools |
| `workspace\` | where the AI works: `videos\`, `projects\`, `assets\`, `review\`, `CLAUDE.md`, `AGENTS.md`, `ASSETS.md`, `tools\find_asset.py` |

## Licence

The app's code is MIT (see `LICENSE`). Assets keep their own licences: [ASSET-LICENSES.md](ASSET-LICENSES.md).
