"""Build the public asset pack: one zip per Default assets folder, holding only files whose licences allow re-sharing
(everything not listed in app/data/restricted-assets.json).

    app\\python\\python.exe app\\tools\\make_asset_pack.py <output folder>

Each zip unpacks into workspace\\assets\\ (its entries start with "Default assets/").
"""
import json, shutil, sys, zipfile
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
WS = APP.parent / "workspace"
SRC = WS / "assets" / "Default assets"
STORE = {".mp3", ".mp4", ".webm", ".png", ".jpg", ".jpeg", ".webp", ".glb", ".hdr", ".exr", ".zip", ".ogg", ".woff2"}


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    restricted = tuple(json.loads((APP / "data" / "restricted-assets.json").read_text(encoding="utf-8"))["folders"])
    total = 0
    for top in sorted(p for p in SRC.iterdir() if p.is_dir()):
        files = [f for f in sorted(top.rglob("*")) if f.is_file()
                 and not f.relative_to(WS).as_posix().startswith(restricted)]
        if not files: print(f"  skip {top.name} (not shareable)"); continue
        zp = out / f"Default assets - {top.name}.zip"; tmp = zp.with_suffix(".zip.part")
        with zipfile.ZipFile(tmp, "w", allowZip64=True) as z:
            for f in files:
                comp = zipfile.ZIP_STORED if f.suffix.lower() in STORE else zipfile.ZIP_DEFLATED
                z.write(f, "Default assets/" + f.relative_to(SRC).as_posix(), compress_type=comp)
        tmp.replace(zp)
        size = zp.stat().st_size; total += size
        print(f"  {zp.name}: {len(files)} files, {size / 1e6:.0f} MB", flush=True)
    shutil.copy2(APP.parent / "ASSET-LICENSES.md", out / "ASSET-LICENSES.md")
    (out / "README.txt").write_text(
        "AI Video Editor - Default assets (the freely shareable part)\n\n"
        "Unzip every 'Default assets - *.zip' into the app's workspace\\assets\\ folder, so you get\n"
        "workspace\\assets\\Default assets\\3D, Emoji, Fonts, ... Then restart the app.\n"
        "Or simply ask Claude Code, opened in the app folder: 'Install the default assets from this Google Drive folder'.\n"
        "Sources and licences: ASSET-LICENSES.md\n", encoding="utf-8")
    print(f"Done: {total / 1e9:.2f} GB in {out}")


if __name__ == "__main__":
    main(sys.argv[1])
