"""Download the Mixkit music, sound effects and stock footage of the Default assets straight from Mixkit.

    app\\python\\python.exe app\\tools\\fetch_mixkit_assets.py [--only music|sfx|footage] [--workers 6]

Mixkit items are free to use in your videos (Mixkit licence) but may not be re-shared as files, so they are not in the
public asset pack: every user fetches them from Mixkit with this script (about 2.6 GB). Safe to run again: files already
on disk are skipped. Restart the Review Room afterwards so the asset browser lists them.
"""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
WS = APP.parent / "workspace"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ReviewRoom-asset-fetch"}


def fetch(item):
    out = WS / item["path"]
    if out.exists() and out.stat().st_size > 0: return "skip"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".part")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(item["url"], headers=UA), timeout=60) as r, open(tmp, "wb") as f:
                while chunk := r.read(1 << 16): f.write(chunk)
            tmp.replace(out); return "ok"
        except Exception as e:
            err = e; time.sleep(2 * (attempt + 1))
    tmp.unlink(missing_ok=True)
    return f"failed: {item['url']} ({err})"


def main(argv):
    items = json.loads((APP / "data" / "mixkit-catalog.json").read_text(encoding="utf-8"))
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    folder = {"music": "/Music/", "sfx": "/Sound effects/", "footage": "/Footage/"}.get(only or "", "")
    items = [i for i in items if folder in i["path"]]
    workers = int(argv[argv.index("--workers") + 1]) if "--workers" in argv else 6
    done = ok = skip = 0; fails = []
    with ThreadPoolExecutor(workers) as pool:
        for res in pool.map(fetch, items):
            done += 1
            if res == "ok": ok += 1
            elif res == "skip": skip += 1
            else: fails.append(res)
            if done % 50 == 0 or done == len(items): print(f"  {done}/{len(items)}  new {ok}  already there {skip}  failed {len(fails)}", flush=True)
    for f in fails[:20]: print(" ", f)
    print("Done. Restart the Review Room so the asset browser lists the new files.")


if __name__ == "__main__":
    main(sys.argv[1:])
