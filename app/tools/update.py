r"""Safe self-update for the AI Video Editor (run by Claude or Codex when the user presses "Let Claude update").

    app\python\python.exe app\tools\update.py --check       # installed version vs the newest on GitHub
    app\python\python.exe app\tools\update.py --plan        # download the newest version and show what would change (writes nothing)
    app\python\python.exe app\tools\update.py --apply       # back up, update, verify; rolls itself back if anything fails
    app\python\python.exe app\tools\update.py --rollback [backups\<folder>]   # undo an update (default: the newest backup)

Rules (app/data/update-manifest.json):
- Only "app_owned" files are replaced, and each replaced or removed file is first copied to backups\<old version>-<time>\.
- "user_owned" paths are never written, moved or deleted: settings.json, workspace\videos, projects, assets, review,
  ASSETS.md, ASSET-NOTES.md, the installed skills, backups\ and the portable Python. A fingerprint of them is taken
  before and after, and the update is rolled back if anything there changed.
- settings.json only gains keys that are new in app\data\settings.default.json; your values stay.
- A file you changed yourself (it differs from what the installed version shipped, app\data\installed-files.json) is kept;
  the new version is saved beside it as "<file>.update-new" for Claude to merge by hand.
- A git clone with no local changes updates with `git pull --ff-only` instead.
The last line printed is `UPDATE_RESULT {json}`.
"""
import hashlib, json, os, py_compile, shutil, subprocess, sys, tempfile, time, urllib.request, zipfile
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
ROOT = APP.parent
MANIFEST = json.loads((APP / "data" / "update-manifest.json").read_text(encoding="utf-8"))
BACKUPS = ROOT / "backups"
STAGE = BACKUPS / ".staging"
UA = {"User-Agent": "ai-video-editor-updater"}


def vtuple(v): return tuple(int(x) for x in "".join(c for c in v.strip() if c.isdigit() or c == ".").split(".") if x)


def local_version():
    try: return (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError: return "1.0.0"                                   # 1.0.0 shipped without a VERSION file


def latest_version(timeout=15):
    url = f"https://raw.githubusercontent.com/{MANIFEST['repo']}/{MANIFEST['branch']}/VERSION"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8").strip()


def owner(rel):
    """'app' or 'user' by the longest matching prefix in the manifest (user wins ties: safer)"""
    best, who = -1, "app"
    for kind, key in (("app", "app_owned"), ("user", "user_owned")):
        for pre in MANIFEST[key]:
            if (rel == pre.rstrip("/") or rel.startswith(pre if pre.endswith("/") else pre + "/") or rel == pre) and len(pre) >= best:
                best, who = len(pre), kind
    return who


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def norm_text_sha(p):
    """hash that ignores CRLF/LF differences (git on Windows may convert line endings)"""
    data = Path(p).read_bytes()
    if b"\0" not in data[:8000]: data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def user_fingerprint():
    """sizes + modification times of every user-owned file (review/ is skipped: the running app writes logs there)"""
    h, n = hashlib.sha1(), 0
    for pre in MANIFEST["user_owned"]:
        if pre in ("backups/", "workspace/review/", "app/python/"): continue
        base = ROOT / pre
        files = [base] if base.is_file() else (sorted(base.rglob("*")) if base.exists() else [])
        for f in files:
            if not f.is_file(): continue
            rel = f.relative_to(ROOT).as_posix()
            if owner(rel) != "user" or rel == "settings.json": continue
            st = f.stat(); h.update(f"{rel}|{st.st_size}|{int(st.st_mtime)}\n".encode("utf-8", "replace")); n += 1
    return {"files": n, "sum": h.hexdigest()}


def download(dst):
    url = f"https://codeload.github.com/{MANIFEST['repo']}/zip/refs/heads/{MANIFEST['branch']}"
    print(f"downloading {url}")
    if STAGE.exists(): shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    zp = STAGE / "new.zip"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, open(zp, "wb") as f:
        shutil.copyfileobj(r, f)
    with zipfile.ZipFile(zp) as z:
        for m in z.infolist():
            parts = Path(m.filename).parts
            if len(parts) < 2 or m.is_dir(): continue
            rel = Path(*parts[1:])
            if rel.is_absolute() or ".." in rel.parts: raise RuntimeError(f"unsafe path in the download: {m.filename}")
            out = dst / rel; out.parent.mkdir(parents=True, exist_ok=True)
            with z.open(m) as src, open(out, "wb") as f: shutil.copyfileobj(src, f)
    zp.unlink()
    return dst


def plan(new_root):
    old_manifest = {}
    try: old_manifest = json.loads((APP / "data" / "installed-files.json").read_text(encoding="utf-8"))
    except Exception: pass
    new_files = {p.relative_to(new_root).as_posix(): p for p in new_root.rglob("*") if p.is_file()}
    P = {"add": [], "replace": [], "conflict": [], "remove": [], "keep_removed": [], "skip_user": []}
    for rel, src in sorted(new_files.items()):
        if owner(rel) == "user": P["skip_user"].append(rel); continue
        dst = ROOT / rel
        if not dst.exists(): P["add"].append(rel); continue
        if norm_text_sha(dst) == norm_text_sha(src): continue
        shipped = old_manifest.get(rel)
        if shipped and norm_text_sha(dst) != shipped: P["conflict"].append(rel)
        else: P["replace"].append(rel)
    for rel, shipped in sorted(old_manifest.items()):
        if rel in new_files or owner(rel) == "user" or not (ROOT / rel).exists(): continue
        (P["remove"] if norm_text_sha(ROOT / rel) == shipped else P["keep_removed"]).append(rel)
    return P


def merge_settings(new_root):
    d = new_root / "app" / "data" / "settings.default.json"
    defaults = json.loads(d.read_text(encoding="utf-8")) if d.exists() else {}
    sp = ROOT / "settings.json"
    cur = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    added = [k for k in defaults if k not in cur]
    if added or not sp.exists():
        merged = {**defaults, **cur}
        sp.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return added, cur


def verify():
    errors = []
    for f in list((APP).rglob("*.py")) + list((ROOT / "workspace" / "tools").rglob("*.py")):
        if "python" in f.relative_to(APP).parts[:1]: continue
        try: py_compile.compile(str(f), cfile=os.path.join(tempfile.gettempdir(), "rr_update_check.pyc"), doraise=True)
        except py_compile.PyCompileError as e: errors.append(f"{f.relative_to(ROOT)}: {e.msg[:200]}")
    for need in ("app/server.py", "app/static/index.html", "app/static/app.js", "VERSION", "Start Review Room.vbs"):
        if not (ROOT / need).exists(): errors.append(f"missing {need}")
    return errors


def rollback(bdir=None):
    bdir = Path(bdir) if bdir else max((p for p in BACKUPS.iterdir() if p.is_dir() and not p.name.startswith(".")), key=lambda p: p.stat().st_mtime)
    meta = json.loads((bdir / "plan.json").read_text(encoding="utf-8"))
    for rel in meta.get("add", []):
        (ROOT / rel).unlink(missing_ok=True)
    for f in (bdir / "files").rglob("*"):
        if f.is_file():
            dst = ROOT / f.relative_to(bdir / "files"); dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, dst)
    print(f"rolled back from {bdir}")
    return bdir


def git_update():
    """a clean git clone: fast-forward pull (settings.json, tracked in 1.0.0, is kept)"""
    if not ((ROOT / ".git").exists() and shutil.which("git")): return None
    g = lambda *a: subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)
    dirty = [l[3:] for l in g("status", "--porcelain", "--untracked-files=no").stdout.splitlines()]
    if [d for d in dirty if d != "settings.json"]: return None          # your own changes: use the file method instead
    keep = (ROOT / "settings.json").read_bytes() if (ROOT / "settings.json").exists() else None
    if "settings.json" in dirty: g("checkout", "--", "settings.json")
    r = g("pull", "--ff-only", "origin", MANIFEST["branch"])
    if keep is not None: (ROOT / "settings.json").write_bytes(keep)
    if r.returncode: raise RuntimeError("git pull failed: " + (r.stderr or r.stdout)[-400:])
    return r.stdout.strip()


def result(**kw):
    print("UPDATE_RESULT " + json.dumps(kw, ensure_ascii=False))
    return kw


def main(argv):
    old = local_version()
    if "--rollback" in argv:
        i = argv.index("--rollback"); b = argv[i + 1] if len(argv) > i + 1 else None
        rollback(b); return result(ok=True, rolled_back=True)
    try: new = latest_version()
    except Exception as e: return result(ok=False, error=f"cannot reach GitHub: {e}", installed=old)
    if "--check" in argv or vtuple(new) <= vtuple(old):
        return result(ok=True, installed=old, latest=new, update_available=vtuple(new) > vtuple(old))
    before = user_fingerprint()
    if "--apply" in argv:
        try:
            out = git_update()
            if out is not None:
                added, _ = merge_settings(ROOT)
                errs = verify(); after = user_fingerprint()
                if errs or after != before:
                    return result(ok=False, method="git", error="verify failed: " + "; ".join(errs or ["user files changed"]),
                                  hint="run `git log` / `git reflog` and reset to the previous commit")
                return result(ok=True, method="git", installed=new, previous=old, settings_added=added, git=out[-500:])
        except Exception as e:
            return result(ok=False, method="git", error=str(e))
    new_root = download(STAGE / "new")
    P = plan(new_root)
    print(f"{old} -> {new}: add {len(P['add'])}, replace {len(P['replace'])}, remove {len(P['remove'])}, "
          f"conflicts {len(P['conflict'])} (your edited files), user files skipped {len(P['skip_user'])}")
    for k in ("add", "replace", "remove", "conflict", "keep_removed"):
        for rel in P[k]: print(f"  {k:12} {rel}")
    if "--apply" not in argv:
        return result(ok=True, planned=True, installed=old, latest=new, **{k: len(v) for k, v in P.items()})
    bdir = BACKUPS / f"{old}-{time.strftime('%Y%m%d-%H%M%S')}"
    (bdir / "files").mkdir(parents=True)
    (bdir / "plan.json").write_text(json.dumps({"from": old, "to": new, **P}, indent=1), encoding="utf-8")
    try:
        for rel in P["replace"] + P["remove"]:
            dst = bdir / "files" / rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / rel, dst)
        for rel in P["add"] + P["replace"]:
            dst = ROOT / rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(new_root / rel, dst)
        for rel in P["conflict"]:
            shutil.copy2(new_root / rel, ROOT / (rel + ".update-new"))
        for rel in P["remove"]:
            (ROOT / rel).unlink(missing_ok=True)
        added, _ = merge_settings(new_root)
        errs = verify()
        after = user_fingerprint()
        if after != before: errs.append("a user file changed during the update")
        if errs: raise RuntimeError("; ".join(errs))
    except Exception as e:
        rollback(bdir)
        return result(ok=False, error=f"update failed and was rolled back: {e}", backup=str(bdir.relative_to(ROOT)))
    shutil.rmtree(STAGE, ignore_errors=True)
    return result(ok=True, method="files", installed=new, previous=old, backup=str(bdir.relative_to(ROOT)),
                  replaced=len(P["replace"]), added=len(P["add"]), removed=len(P["remove"]), settings_added=added,
                  conflicts=[r + ".update-new" for r in P["conflict"]], user_files_checked=before["files"])


if __name__ == "__main__":
    r = main(sys.argv[1:])
    sys.exit(0 if r.get("ok") else 1)
