"""Free, offline drop-in for transcribe.py (Review Room addition): whisper.cpp (CUDA, large-v3-turbo, DTW word
timing) instead of the paid ElevenLabs Scribe API. Writes the same Scribe-shaped JSON to <edit>/transcripts/<stem>.json,
so pack_transcripts.py, render.py and the rest of video-use work unchanged.

    python transcribe_local.py <video> [--edit-dir DIR] [--language ar|en|...] [--audio-track N] [--prompt "..."]
    python transcribe_local.py <videos_dir> --batch [...]      # every video in the folder, cached

Needs HYPERFRAMES_WHISPER_PATH (whisper-cli.exe) and ~/.cache/hyperframes/whisper/models/ggml-large-v3-turbo.bin
(tools/setup_windows.ps1 installs both). For Arabic always pass --language ar. Word edges from whisper can drift
50-150 ms; keep video-use's 30-200 ms cut padding. For voice-over takes where cuts must sit exactly between words,
use a forced aligner (e.g. wav2vec2) instead.
No speaker diarization: every word gets speaker_0.
"""
import argparse, json, os, re, subprocess, sys, tempfile
from pathlib import Path

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".mts", ".mxf", ".wav", ".mp3", ".m4a", ".flac"}


def whisper_bin():
    p = os.environ.get("HYPERFRAMES_WHISPER_PATH") or str(Path(os.environ.get("LOCALAPPDATA", "")) / "whisper.cpp-cuda/Release/whisper-cli.exe")
    if not Path(p).exists():
        sys.exit("whisper-cli not found: set HYPERFRAMES_WHISPER_PATH (run Setup.bat, speech option)")
    return p


def model_path(name):
    p = Path.home() / ".cache/hyperframes/whisper/models" / f"ggml-{name}.bin"
    if not p.exists():
        sys.exit(f"whisper model missing: {p}")
    return p


def transcribe_one(video: Path, edit_dir: Path, language=None, audio_track=0, prompt=None, model="large-v3-turbo"):
    out = edit_dir / "transcripts" / (video.stem + ("" if audio_track == 0 else f".track{audio_track}") + ".json")
    if out.exists():
        print(f"cached: {out.name}"); return out
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-map", f"0:a:{audio_track}", "-vn", "-ac", "1",
                        "-ar", "16000", "-c:a", "pcm_s16le", str(wav)], check=True)
        base = Path(tmp) / "w"
        cmd = [whisper_bin(), "-m", str(model_path(model)), "-f", str(wav), "-ml", "1", "-sow", "-ojf", "-of", str(base),
               "-dtw", model.replace("-", ".").replace("large.v3.turbo", "large.v3.turbo"), "-l", language or "auto", "-np"]
        if prompt: cmd += ["--prompt", prompt]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not (base.with_suffix(".json")).exists():
            # some builds reject -dtw for a model name; retry without it
            cmd = [c for i, c in enumerate(cmd) if c != "-dtw" and (i == 0 or cmd[i - 1] != "-dtw")]
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        j = json.loads(base.with_suffix(".json").read_text(encoding="utf-8", errors="replace"))

    words = []
    for seg in j.get("transcription", []):
        for tok in seg.get("tokens", []):
            t = tok.get("text", "")
            if not t.strip() or re.fullmatch(r"\[_?[A-Z_]+\d*_?\]|<\|.*\|>", t.strip()):
                continue
            s = tok.get("offsets", {}).get("from", 0) / 1000.0
            e = tok.get("offsets", {}).get("to", 0) / 1000.0
            if "t_dtw" in tok and tok["t_dtw"] >= 0:
                s = max(s, tok["t_dtw"] / 100.0 - 0.05)
            if t.startswith(" ") or not words:
                words.append({"text": t.strip(), "start": round(s, 3), "end": round(e, 3), "type": "word", "speaker_id": "speaker_0"})
            else:                                   # sub-word token: glue onto the previous word
                words[-1]["text"] += t; words[-1]["end"] = round(e, 3)
    scribe = []
    for i, w in enumerate(words):
        if i:
            gap_s = words[i - 1]["end"]
            if w["start"] > gap_s:
                scribe.append({"text": " ", "start": gap_s, "end": w["start"], "type": "spacing", "speaker_id": "speaker_0"})
        scribe.append(w)
    payload = {"language_code": (j.get("result", {}) or {}).get("language", language or ""),
               "text": " ".join(w["text"] for w in words), "words": scribe, "engine": "whisper.cpp " + model}
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  saved: {out.name}  words: {len(words)}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", type=Path)
    ap.add_argument("--edit-dir", type=Path)
    ap.add_argument("--language")
    ap.add_argument("--audio-track", type=int, default=0)
    ap.add_argument("--prompt")
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--batch", action="store_true")
    a = ap.parse_args()
    p = a.path.resolve()
    vids = sorted(x for x in p.iterdir() if x.suffix.lower() in VIDEO_EXT) if a.batch else [p]
    edit = (a.edit_dir or ((p if a.batch else p.parent) / "edit")).resolve()
    for v in vids:
        print(v.name); transcribe_one(v, edit, a.language, a.audio_track, a.prompt, a.model)


if __name__ == "__main__":
    main()
