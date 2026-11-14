r"""Learn the asset library: index every file under workspace/assets and write a guide the AI reads before each job.

    app\python\python.exe app\tools\learn_assets.py           # learn now (the app also does this by itself)
    app\python\python.exe app\tools\learn_assets.py --check   # only say whether the library changed since the last learn

Writes (all user data, never replaced by an update):
  workspace/review/asset-index.json   every asset: kind, path, name, folder (find_asset.py and the app search this)
  workspace/ASSETS.md                 what is in the library and how to use each kind in HyperFrames, ffmpeg and Blender
  workspace/review/asset-state.json   fingerprint of the library, so a change (assets installed, added, removed) is noticed
The shipped index (app/data/default-assets.json) only adds nicer names; files are found by walking the disk.
"""
import json, os, sys, time
from collections import Counter, defaultdict
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
WS = APP.parent / "workspace"
LIB = WS / "assets" / "Default assets"
INDEX, STATE, GUIDE = WS / "review" / "asset-index.json", WS / "review" / "asset-state.json", WS / "ASSETS.md"

TOP_KIND = {"Music": "music", "Sound effects": "sfx", "Footage": "footage", "Icons": "icon", "Emoji": "emoji", "Fonts": "font",
            "3D": "3d", "Looks (LUTs)": "lut", "Illustrations": "image", "Brands": "brand", "Voice samples": "audio", "Maps": "map"}
EXT = {**{e: "image" for e in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")},
       **{e: "footage" for e in (".mp4", ".mov", ".webm", ".mkv", ".m4v")},
       **{e: "audio" for e in (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus")},
       **{e: "font" for e in (".ttf", ".otf", ".woff", ".woff2")}, ".cube": "lut",
       **{e: "3d" for e in (".glb", ".gltf", ".fbx", ".obj", ".blend", ".stl", ".hdr", ".exr")},
       ".json": "lottie", ".lottie": "lottie", ".geojson": "map", ".topojson": "map", ".shp": "map"}
SKIP_EXT = {".txt", ".md", ".html", ".htm", ".pdf", ".url", ".ini", ".db", ".license", ".py", ".css", ".js", ".xml", ".csv"}

HOW = {
    "music": "background music. ffmpeg: mix under speech with `sidechaincompress` or a volume duck; finish at -14 LUFS. "
             "HyperFrames: an `<audio>` clip with `data-start`/`data-duration`/`data-volume`.",
    "sfx": "sound effects. Place on cuts and motion hits; keep them 6-12 dB under the voice. Same tools as music.",
    "audio": "voice / audio samples.",
    "footage": "stock video (b-roll, overlays, textures). Cut with ffmpeg `-ss/-t`, or a HyperFrames `<video>` clip with "
               "`data-media-start`. Overlays (smoke, light leaks, film grain): blend modes `screen`/`overlay`.",
    "image": "pictures and illustrations (PNG/SVG). HyperFrames `<img>`; ffmpeg `overlay`.",
    "icon": "SVG icons. Inline the SVG in HyperFrames to recolour it with CSS (`fill: currentColor`).",
    "emoji": "emoji (Fluent 3D PNG, Twemoji SVG, Noto animated Lottie/GIF). Animated ones: lottie-web in HyperFrames.",
    "lottie": "Lottie animations (.json): play with lottie-web in HyperFrames, seeked by the timeline.",
    "font": "fonts. HyperFrames: `@font-face { src: url(...) }` with the file copied into the project. Arabic text: an Arabic "
            "font, `dir=\"rtl\"`, never letter-spacing (it breaks joined letters).",
    "lut": ".cube colour looks. ffmpeg `lut3d=file.cube` (blend with the original for strength); the app's own looks are in ../app/luts.",
    "3d": "3D: HDRIs (.hdr/.exr: Blender world light, or Three.js environment), PBR textures, models (.glb/.gltf/.fbx/.obj/.stl: "
          "Blender import, or Three.js GLTFLoader in HyperFrames).",
    "map": "maps (GeoJSON / shapefiles): draw with SVG/d3-geo in HyperFrames for animated maps.",
    "brand": "the user's brand files (logos). Use only for that brand.",
    "file": "other files.",
}


def load(p, default):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception: return default


def walk():
    """[(workspace-relative path, size)] for every file under workspace/assets (Default assets and the user's own files)"""
    out, base = [], WS / "assets"
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        rel = Path(dirpath).relative_to(WS).as_posix()
        for f in files:
            if f.startswith(".") or f == "desktop.ini": continue
            try: out.append((f"{rel}/{f}", os.path.getsize(os.path.join(dirpath, f))))
            except OSError: pass
    return out


def fingerprint(files=None):
    files = walk() if files is None else files
    return {"files": len(files), "bytes": sum(s for _, s in files), "sum": hash_paths(files)}


def hash_paths(files):
    import hashlib
    h = hashlib.sha1()
    for p, s in sorted(files): h.update(f"{p}|{s}\n".encode("utf-8", "replace"))
    return h.hexdigest()


def kind_of(path):
    parts = path.split("/")
    ext = Path(path).suffix.lower()
    if ext in SKIP_EXT: return None
    top = parts[2] if len(parts) > 3 and parts[1] == "Default assets" else None
    k = EXT.get(ext, "file")
    tk = TOP_KIND.get(top or "")
    if tk and k in ("audio", "file") and tk in ("music", "sfx", "audio"): return tk
    if tk == "emoji" and k in ("image", "lottie"): return "emoji" if k == "image" else "lottie"
    if tk in ("icon",) and k == "image": return "icon"
    if tk == "brand" and k in ("image", "file"): return "brand"
    if tk == "map" and k in ("file", "lottie"): return "map"
    return k


def learn(quiet=False):
    t0 = time.time()
    files = walk()
    shipped = {i["path"]: i for i in load(APP / "data" / "default-assets.json", [])}
    items = []
    for path, size in files:
        it = shipped.get(path)
        if it: items.append(dict(it)); continue
        k = kind_of(path)
        if not k: continue
        parts = path.split("/")
        items.append({"kind": k, "path": path, "name": Path(path).stem.replace("_", " ").replace("-", " "),
                      "sub": parts[-2] if len(parts) > 2 else "", **({} if parts[1] == "Default assets" else {"mine": True})})
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    write_guide(items, dict(files))
    st = {"fingerprint": fingerprint(files), "learned": time.time(), "count": len(items),
          "by_kind": dict(Counter(i["kind"] for i in items).most_common())}
    STATE.write_text(json.dumps(st, indent=1), encoding="utf-8")
    if not quiet: print(f"learned {len(items)} assets in {time.time() - t0:.1f}s -> {GUIDE}")
    return st


def changed():
    st = load(STATE, {})
    return st.get("fingerprint") != fingerprint(), st


def write_guide(items, sizes):
    restricted = load(APP / "data" / "restricted-assets.json", {}).get("folders", {})
    by_top = defaultdict(list)
    for i in items:
        p = i["path"].split("/")
        by_top[p[2] if p[1] == "Default assets" and len(p) > 3 else "(your own files)"].append(i)
    L = ["# The asset library (learned automatically)", "",
         f"Learned {time.strftime('%Y-%m-%d %H:%M')}: **{len(items):,} assets**. Re-learned by the app whenever files are added or removed.",
         "Search it: `../app/python/python.exe tools/find_asset.py <words> [--kind KIND] [-n 25] [--no-slop]` "
         "(KIND: music sfx audio footage image icon emoji lottie font lut 3d map brand effect file).",
         "Use the library before generating, drawing or downloading anything. Copy the files you use into the project's `src/`.",
         ""]
    if restricted:
        L += ["Folders whose licence forbids re-sharing the files (fine inside videos; skip them when the job says only shareable "
              "assets): " + ", ".join(f"`{f}`" for f in restricted), ""]
    L += ["## What is where", ""]
    for top in sorted(by_top):
        its = by_top[top]
        mb = sum(sizes.get(i["path"], 0) for i in its) / 1e6
        kinds = Counter(i["kind"] for i in its)
        L.append(f"### {top}: {len(its):,} files, {mb:,.0f} MB ({', '.join(f'{k} {n:,}' for k, n in kinds.most_common())})")
        def group(i):
            parts = i["path"].split("/")[:-1]                     # the folder, at most two levels below the top folder
            parts = parts[3:5] if top != "(your own files)" else parts[2:4]
            return "/".join(parts) or "(top level)"
        subs, groups = Counter(), defaultdict(list)
        for i in its:
            g = group(i); subs[g] += 1
            if len(groups[g]) < 3: groups[g].append(i["name"])
        for sub, n in subs.most_common(14):
            L.append(f"- `{sub}`: {n:,} (e.g. {', '.join(groups[sub])})")
        if len(subs) > 14: L.append(f"- … and {len(subs) - 14} more folders")
        L.append("")
    L += ["## How to use each kind", ""]
    present = Counter(i["kind"] for i in items)
    for k, how in HOW.items():
        if present.get(k): L.append(f"- **{k}** ({present[k]:,}): {how}")
    L += ["", "If `ASSET-NOTES.md` exists next to this file, read it too: it holds the AI's own notes from studying the library "
          "(best picks per mood, Arabic fonts that work, sound sets that belong together)."]
    GUIDE.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if "--check" in sys.argv:
        c, st = changed()
        print("changed since the last learn" if c else f"up to date ({st.get('count', 0)} assets)")
    else:
        learn()
