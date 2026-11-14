# Changelog

## 1.3.0 (2026-11-14)

- **New interface**, designed by Codex (GPT-6.1-sol) and checked by Claude: a "cutting room" look with warm charcoal surfaces,
  ivory type and ochre controls, line icons instead of emoji, and the picture as the hero. Every screen, panel and dialog was
  redrawn; all functions, shortcuts and settings work as before.
- Local fonts (no internet needed): Manrope and IBM Plex Sans Arabic, both under the SIL Open Font License
  (`app/static/*-OFL.txt`).

## 1.2.0 (2026-11-14)

- **Claude, Codex or both:** `Codex Login.bat` signs in with ChatGPT or a hidden API key, tests the connection,
  signs out and offers CLI updates. Setup offers Codex and opens both sign-in menus (Enter or 0 skips each).
- **Newest Codex CLI:** the app compares installed versions from your settings, the Codex desktop app, sandbox-bin
  and PATH / npm, and uses the newest. It checks again every ten minutes.
- Codex now uses `gpt-6.1-sol` by default, with one retry on `gpt-5.6-sol` if the model is not supported. Normal edits
  still use medium effort; heavy edits use high effort. Current Codex conversation resumes keep sandbox options.
- The header and Settings show both engines' sign-in state, models and the Codex account and CLI version. Each engine
  stays selectable; a job sent without signing in explains which login tool to run.

## 1.1.0 (2026-11-14)

- **Updates:** the app checks GitHub for a new version. **Let Claude update** has Claude (or Codex) run the safe updater:
  it backs up every file it replaces into `backups\`, never touches your videos, projects, assets, notes or settings,
  verifies the result and rolls back on any error. Then the app closes, and you open the new version.
- **Quick preview:** with ⚡ Quick preview on, the AI makes the edit and renders only a fast draft (same timing, lower
  quality). When you are happy, press **Render final**: the app renders the full-quality version from the AI's saved recipe,
  without another AI job.
- **Asset learning:** when assets are installed, added or removed, the app re-indexes them and writes `workspace\ASSETS.md`
  (what is where, and how to use each kind). **Let the AI study them** has the AI write `ASSET-NOTES.md` with its best
  picks per mood and purpose.
- **NVIDIA, AMD and Intel GPUs:** the app tests what works on your PC (NVENC / AMF / Quick Sync encoders, Blender
  CUDA / OptiX / HIP / oneAPI, whisper on CUDA or CPU) and tells the AI to use it. Setup installs the matching whisper build.
- Settings now come from `app\data\settings.default.json`, with your own values in `settings.json` (no longer part of the
  repo, so updates never overwrite it).

## 1.0.0 (2026-11-14)

- First public release: Review Room editor, Make a video, 37 styles, Claude and Codex engines, the asset library,
  Remove AI slop audio, and the security fixes from the penetration test.
