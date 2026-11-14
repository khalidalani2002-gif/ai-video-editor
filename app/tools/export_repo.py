"""Copy a clean, shareable copy of the app into a git folder (no user videos, notes, assets, portable Python or private data).

    app\\python\\python.exe app\\tools\\export_repo.py <repo folder>
"""
import json, shutil, sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent.parent              # the ReviewRoom folder
PRIVATE = ("assets/Default assets/Brands/", "assets/Default assets/Arabic/", "assets/Default assets/Voice samples/",
           "assets/Default assets/Sound effects/Pro (curated)/")   # never shared, and not downloadable anywhere
FILES = ["Start Review Room.vbs", "Setup.bat", "Claude Login.bat", "README.md", "ASSET-LICENSES.md", "LICENSE",
         "app/server.py", "app/ai_tools.py", "app/setup.ps1", "app/make_shortcut.ps1", "app/icon.ico", "app/icon.svg",
         "app/tools/import_default_assets.py", "app/tools/fetch_mixkit_assets.py", "app/tools/make_asset_pack.py",
         "app/tools/export_repo.py", "app/tools/style_examples/render_3d.py", "app/tools/style_examples/make_2d.py",
         "workspace/CLAUDE.md", "workspace/AGENTS.md", "workspace/tools/find_asset.py"]
DIRS = ["app/static", "app/luts", "workspace/.claude/skills/video-use"]
DATA = ["styles.json", "slop-audio.json", "restricted-assets.json", "mixkit-catalog.json", "hyperframes-registry.json"]
SETTINGS = {"port": 8770, "whisper_port": 8771, "model": "claude-opus-5-5", "codex_model": "gpt-5.6-sol", "codex_sandbox": "", "use_restricted_assets": True}
GITATTRIBUTES = """* text=auto
*.bat text eol=crlf
*.vbs text eol=crlf
*.ps1 text eol=crlf
*.jpg binary
*.png binary
*.ico binary
"""
GITIGNORE = """# user data and big local files (never committed)
app/python/
**/__pycache__/
app/tools/style_examples/out/
app/tools/style_examples/html/
app/tools/style_examples/.chrome-profile/
workspace/videos/*
workspace/projects/*
workspace/assets/*
workspace/review/*
!**/.gitkeep
"""


def main(dst):
    dst = Path(dst); dst.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        (dst / f).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(SRC / f, dst / f)
    for d in DIRS:
        if (dst / d).exists(): shutil.rmtree(dst / d)
        shutil.copytree(SRC / d, dst / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (dst / "app" / "data").mkdir(parents=True, exist_ok=True)
    for f in DATA: shutil.copy2(SRC / "app" / "data" / f, dst / "app" / "data" / f)
    idx = json.loads((SRC / "app" / "data" / "default-assets.json").read_text(encoding="utf-8"))
    pub = [i for i in idx if not i["path"].startswith(PRIVATE)]
    (dst / "app" / "data" / "default-assets.json").write_text(json.dumps(pub, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (dst / "settings.json").write_text(json.dumps(SETTINGS, indent=2) + "\n", encoding="utf-8")
    for d in ("workspace/videos", "workspace/projects", "workspace/assets", "workspace/review"):
        (dst / d).mkdir(parents=True, exist_ok=True); (dst / d / ".gitkeep").write_text("", encoding="utf-8")
    (dst / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (dst / ".gitattributes").write_text(GITATTRIBUTES, encoding="utf-8")
    print(f"exported to {dst}: index {len(pub)} of {len(idx)} assets")


if __name__ == "__main__":
    main(sys.argv[1])
