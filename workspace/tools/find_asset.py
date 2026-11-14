"""Search the Review Room asset library (Default assets + your own files + HyperFrames effects + looks).

    ../app/python/python.exe tools/find_asset.py WORDS... [--kind KIND] [-n 25] [--no-slop]
    ../app/python/python.exe tools/find_asset.py --summary

KIND: music sfx audio footage image icon emoji brand font lut 3d effect lottie file
--no-slop  hide the overused "AI video" sounds listed in ../app/data/slop-audio.json (required when the job says so)
Every word must match (name, folder or tags). Paths printed are relative to the workspace folder.
"""
import json, os, sys
from collections import Counter
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
APP = WS.parent / "app"
EXT = {**{e: "image" for e in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")}, **{e: "footage" for e in (".mp4", ".mov", ".webm", ".mkv")},
       **{e: "audio" for e in (".mp3", ".wav", ".m4a", ".ogg", ".flac")}, **{e: "font" for e in (".ttf", ".otf", ".woff", ".woff2")},
       ".cube": "lut", **{e: "3d" for e in (".glb", ".gltf", ".fbx", ".obj", ".blend")}}


def load(p, default):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return default


def library():
    settings = load(WS.parent / "settings.json", {})
    blocked = tuple(load(APP / "data" / "restricted-assets.json", {}).get("folders", {})) if settings.get("use_restricted_assets") is False else ()
    present = set()
    for dirpath, _d, files in os.walk(WS / "assets" / "Default assets"):
        rel = Path(dirpath).relative_to(WS).as_posix(); present.update(f"{rel}/{f}" for f in files)
    items = [it for it in load(APP / "data" / "default-assets.json", []) if it["path"] in present and not (blocked and it["path"].startswith(blocked))]
    base = WS / "assets"
    for top in base.iterdir() if base.exists() else []:                 # your own files (never walk Default assets)
        if top.name == "Default assets": continue
        for f in [top] if top.is_file() else top.rglob("*"):
            if f.is_file():
                items.append({"kind": EXT.get(f.suffix.lower(), "file"), "path": f.relative_to(WS).as_posix(), "name": f.stem, "sub": "your file"})
    for e in load(APP / "data" / "hyperframes-registry.json", []):
        items.append({"kind": "effect", "path": f"npx hyperframes add {e['name']}", "name": e.get("title") or e["name"],
                      "sub": " ".join(e.get("tags", [])[:4]), "desc": e.get("description", "")})
    for lut in sorted((APP / "luts").glob("*.cube")):
        items.append({"kind": "lut", "path": f"../app/luts/{lut.name}", "name": lut.stem, "sub": "colour look"})
    return items


def slop_filter():
    s = load(APP / "data" / "slop-audio.json", {})
    folders, files = tuple(s.get("folders", [])), set(s.get("files", []))
    return lambda it: not (it["path"].startswith(folders) or it["path"] in files)


def main(argv):
    if "--summary" in argv:
        c = Counter(); tops = Counter()
        for it in library():
            c[it["kind"]] += 1
            if it["path"].startswith("assets/Default assets/"): tops[it["path"].split("/")[2]] += 1
        print("by kind:", ", ".join(f"{k} {v}" for k, v in c.most_common()))
        print("Default assets folders:", ", ".join(f"{k} {v}" for k, v in sorted(tops.items())))
        return
    kind = argv[argv.index("--kind") + 1] if "--kind" in argv else None
    n = int(argv[argv.index("-n") + 1]) if "-n" in argv else 25
    skip = {i + 1 for i, a in enumerate(argv) if a in ("--kind", "-n")}
    words = [a.lower() for i, a in enumerate(argv) if not a.startswith("-") and i not in skip]
    ok = slop_filter() if "--no-slop" in argv else (lambda it: True)
    hits = []
    for it in library():
        k = it["kind"]
        if kind and not (k == kind or (kind == "audio" and k in ("music", "sfx", "audio"))): continue
        text = f"{it['name']} {it.get('sub', '')} {it['path']} {it.get('desc', '')} {k}".lower()
        if all(w in text for w in words) and ok(it):
            nm = it["name"].lower()
            hits.append((0 if words and nm.startswith(words[0]) else 1, it))
    hits.sort(key=lambda h: h[0])
    print(f"{len(hits)} match{'es' if len(hits) != 1 else ''}" + (f" (kind={kind})" if kind else "") + (" without slop audio" if "--no-slop" in argv else ""))
    for _, it in hits[:n]:
        extra = f"  [{round(it['dur'])} s]" if it.get("dur") else ""
        print(f"[{it['kind']}] {it['path']}  - {it['name']}{(' / ' + it['sub']) if it.get('sub') else ''}{extra}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1:])
