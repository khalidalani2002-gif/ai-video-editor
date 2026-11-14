"""Bring an existing asset library (an "Asset" folder with _catalogs) into this app as  workspace/assets/Default assets/<category>/...

    python app/tools/import_default_assets.py <path to the source "Asset" folder>

Files are HARD-LINKED when the source is on the same drive (no extra disk space; they are still ordinary files, and copying
the ReviewRoom folder elsewhere copies them for real). Otherwise they are copied. It also writes app/data/default-assets.json,
the search index (titles from the library's catalogs, kinds, durations). Safe to run again: existing files are skipped.
"""
import json, os, re, shutil, sys
from pathlib import Path

SRC = Path(sys.argv[1]).resolve()
APP = Path(__file__).resolve().parent.parent
DEST = APP.parent / "workspace" / "assets" / "Default assets"
CAT = SRC / "_catalogs"

TOP = {"brands": "Brands", "music": "Music", "sfx": "Sound effects", "video": "Footage", "iraqi": "Arabic", "emoji": "Emoji",
       "icons": "Icons", "fonts": "Fonts", "luts": "Looks (LUTs)", "3d": "3D", "maps": "Maps", "voice-samples": "Voice samples"}
SUB = {"pro": "Pro (curated)", "sonniss-gdc2026": "Sonniss GDC 2026", "kenney": "Kenney", "fluent-3d": "Fluent 3D",
       "twemoji-svg": "Twemoji", "noto-animated": "Noto animated (Lottie)", "hdri": "HDRI", "models": "Models", "textures": "Textures",
       "arabic": "Arabic", "latin": "Latin", "memes": "Memes", "culture": "Culture", "sounds": "Sounds", "effects": "Effects"}


def skip(parts):
    if parts[0] not in TOP: return True                                       # _catalogs, js, explainers, _downloads.jsonl
    if parts[0] == "iraqi" and parts[1] in ("_meta", "_research"): return True
    if parts[0] == "3d" and parts[1] in ("three",) or parts[-1] == "polyhaven-catalog.json": return True
    if parts[0] == "luts" and not parts[-1].endswith(".cube"): return True     # previews and the index stay behind
    return False


def nice(seg): return SUB.get(seg) or seg[:1].upper() + seg[1:].replace("-", " ").replace("_", " ")


def target(parts):
    top, rest = parts[0], list(parts[1:])
    if top in ("music", "video") and rest and rest[0] == "mixkit": rest = rest[1:]   # Music/<Genre>, Footage/<Topic>
    if top == "sfx" and rest and rest[0] == "mixkit": rest[0] = "Mixkit"
    folders = [nice(s) if i < 2 else s for i, s in enumerate(rest[:-1])]
    return Path(TOP[top], *folders, rest[-1] if rest else parts[-1])


def load(name):
    p = CAT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


titles = {}                                                                      # "Asset/..." -> (title, sub, seconds)
for t in load("mixkit-music.json"): titles[t.get("file", "")] = (t["title"], t.get("genre"), t.get("seconds"))
for t in load("mixkit-sfx.json"): titles[t.get("file", "")] = (t["title"], ", ".join(t.get("tags", [])[:2]), None)
for t in load("mixkit-video.json"): titles[t.get("file", "")] = (t["title"], ", ".join(t.get("tags", [])[:2]), None)
emo = load("emoji.json") or {}
for e in (emo.get("fluent3d", []) if isinstance(emo, dict) else []): titles["Asset/emoji/" + e["file"]] = (e["name"], "Fluent 3D", None)
for e in (emo.get("notoAnimated", []) if isinstance(emo, dict) else []): titles["Asset/emoji/" + e["file"]] = (e["name"], "animated", None)
idx_luts = SRC / "luts" / "index.json"
for e in (json.loads(idx_luts.read_text(encoding="utf-8")) if idx_luts.exists() else []):
    titles["Asset/luts/" + e["file"]] = (e["id"], e.get("description", "")[:40], None)
meta = {}                                                                         # rel -> (kind, duration, wxh)
tsv = CAT / "files.tsv"
if tsv.exists():
    for line in tsv.read_text(encoding="utf-8").splitlines()[1:]:
        rel, _b, k, d, wh = (line.split("\t") + [""] * 5)[:5]
        meta[rel] = (k, float(d) if d else None, wh if wh and wh != "x" else None)


def kind_of(parts, k, ext):
    top = parts[0]
    if top == "brands": return "brand" if ext in (".png", ".jpg", ".jpeg", ".svg", ".webp") else "file"
    if top == "icons": return "icon"
    if top == "emoji": return "lottie" if ext == ".json" else "emoji"
    if top == "luts": return "lut"
    if top == "fonts": return "font"
    if top == "voice-samples": return "audio"
    if top == "maps": return "file"
    if k == "audio" or ext in (".mp3", ".wav", ".ogg", ".flac", ".m4a"): return "music" if top == "music" else "sfx"
    if k == "video" or ext in (".mp4", ".webm", ".mov", ".mkv"): return "footage"
    if top == "3d": return "3d"
    if k in ("image", "vector") or ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"): return "image"
    return "file"


DEST.mkdir(parents=True, exist_ok=True)
same_drive = os.path.splitdrive(str(SRC))[0].lower() == os.path.splitdrive(str(DEST))[0].lower()
index, linked, copied, kept = [], 0, 0, 0
for f in sorted(SRC.rglob("*")):
    if not f.is_file(): continue
    rel = f.relative_to(SRC).as_posix(); parts = rel.split("/")
    if len(parts) < 2 or skip(parts): continue
    out = DEST / target(parts)
    if out.exists(): kept += 1
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            if not same_drive: raise OSError
            os.link(f, out); linked += 1
        except OSError:
            shutil.copy2(f, out); copied += 1
    k, dur, wh = meta.get(rel, ("", None, None))
    title, sub, secs = titles.get("Asset/" + rel, (None, None, None))
    name = title or re.sub(r"^\d+-", "", f.stem).replace("-", " ").replace("_", " ")
    item = {"kind": kind_of(parts, k, f.suffix.lower()), "path": out.relative_to(APP.parent / "workspace").as_posix(), "name": name}
    if sub: item["sub"] = sub
    if secs or dur: item["dur"] = secs or dur
    if wh: item["wh"] = wh
    index.append(item)
(APP / "data").mkdir(exist_ok=True)
(APP / "data" / "default-assets.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"{len(index)} assets: {linked} hard-linked, {copied} copied, {kept} already there -> {DEST}")
