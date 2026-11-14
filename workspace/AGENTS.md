# Review Room workspace (rules for Codex)

The Review Room app runs you (`codex exec`) or Claude Code in this folder. Both follow the same rules:

1. **Read `CLAUDE.md` in this folder first.** It covers the folder layout, how jobs arrive (note / batch / creation /
   approval), the `(rev N)` naming, the `RESULT: <path>` line, the tools, the edit levels and the house rules. Everything in it
   applies to you too.
2. **Skills are in `.claude/skills/<name>/SKILL.md`.** You have no Skill tool: when the prompt or `CLAUDE.md` says "load the
   `hyperframes` skill" (or `ffmpeg`, `video-use`, `media-use`…), open that SKILL.md and the reference files it points to, and
   follow them.
3. The user's pinned frames are attached to the prompt as images and are also in `review/frames/<note id>.png`.
4. Work only inside this folder (plus `../app/luts/` for colour looks). Never delete or overwrite the user's videos: new
   versions go beside them as `<name> (rev N).mp4`, and approvals send old versions to the Recycle Bin (PowerShell:
   `[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(path, 'OnlyErrorDialogs', 'SendToRecycleBin')`).
5. End every job with one line `RESULT: <workspace-relative path of the new video>` (or `RESULT: none`) and a short summary.
