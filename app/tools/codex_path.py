"""Shared Codex discovery and safe account metadata (standard library only)."""
import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
NOWIN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def run(args, timeout=15):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, creationflags=NOWIN)


def version_key(version):
    main, _, prerelease = version.split("+")[0].partition("-")
    return (tuple(map(int, main.split("."))), not prerelease,
            tuple((0, int(part)) if part.isdigit() else (1, part) for part in prerelease.split(".")))


def discover(settings=None):
    if settings is None:
        try: settings = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
        except (OSError, ValueError): settings = {}
    candidates = [settings.get("codex_path")]
    if os.name == "nt":
        try:
            r = run(["powershell", "-NoProfile", "-Command",
                     "Get-AppxPackage -Name OpenAI.Codex | ForEach-Object { Join-Path $_.InstallLocation 'app\\resources\\codex.exe' }"])
            candidates += r.stdout.splitlines()
        except (OSError, subprocess.TimeoutExpired): pass
    candidates.append(str(Path.home() / ".codex" / ".sandbox-bin" / "codex.exe"))
    # Inspect every PATH directory, including npm's native executable behind its wrapper.
    for directory in os.get_exec_path():
        for name in ("codex.exe", "codex", "codex.cmd", "codex.bat"):
            p = Path(directory) / name
            if p.is_file(): candidates.append(str(p))
    candidates.append(shutil.which("codex"))
    npm = Path(os.environ.get("APPDATA", "")) / "npm"
    for c in list(candidates) + [str(npm / "codex.cmd")]:
        if c:
            candidates += [str(p) for p in (Path(c).parent / "node_modules" / "@openai").glob(
                "codex*/**/codex.exe")]
    found, seen = [], set()
    for c in candidates:
        if not c: continue
        p = Path(c).expanduser().resolve()
        key = str(p).lower()
        # Prefer real executables: cmd wrappers corrupt multiline prompts and quoting.
        if key in seen or not p.is_file() or p.suffix.lower() in (".cmd", ".bat", ".ps1"): continue
        if os.name == "nt" and p.suffix.lower() != ".exe": continue
        seen.add(key)
        try:
            r = run([str(p), "--version"])
            m = re.search(r"codex(?:-cli)?\s+(\d+\.\d+\.\d+(?:[-+][\w.-]+)?)", r.stdout)
            if r.returncode == 0 and m:
                v = m.group(1)
                found.append((version_key(v), str(p), v))
        except (OSError, subprocess.TimeoutExpired): pass
    if not found: return {"path": None, "version": None}
    best = max(found, key=lambda x: x[0])
    return {"path": best[1], "version": best[2]}


def account():
    """Only return display fields; never expose credentials or raw token claims."""
    out = {"method": None, "email": None, "plan": None}
    try:
        auth = json.loads((Path.home() / ".codex" / "auth.json").read_text(encoding="utf-8"))
        if auth.get("auth_mode") == "chatgpt": out["method"] = "ChatGPT"
        token = (auth.get("tokens") or {}).get("id_token")
        if token:
            payload = token.split(".")[1]
            claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
            details = claims.get("https://api.openai.com/auth") or {}
            out.update(method="ChatGPT", email=claims.get("email"), plan=details.get("chatgpt_plan_type"))
        if auth.get("auth_mode") == "apikey" or auth.get("OPENAI_API_KEY"):
            out = {"method": "API key", "email": None, "plan": None}
    except (OSError, ValueError, IndexError, TypeError): pass
    return out


def status(binary):
    out = account()
    out["signed_in"] = False
    if binary:
        try: out["signed_in"] = run([binary, "login", "status"]).returncode == 0
        except (OSError, subprocess.TimeoutExpired): pass
    return out


def model_rejected(event):
    if event.get("type") not in ("turn.failed", "error"): return False
    message = json.dumps(event).lower()
    return "model" in message and any(s in message for s in (
        "not supported", "unsupported", "does not exist", "not found", "not available",
        "model_not_found", "do not have access", "don't have access"))


if __name__ == "__main__":
    import sys
    result = discover()
    if "--status" in sys.argv: result.update(status(result["path"]))
    print(json.dumps(result))
