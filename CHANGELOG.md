# Changelog

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
