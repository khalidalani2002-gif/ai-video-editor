r"""Which GPU this PC has and what each tool can do with it: NVIDIA, AMD and Intel.

    app\python\python.exe app\gpu.py            # print the report (Setup runs this)
    app\python\python.exe app\gpu.py --json     # the same as JSON

Every claim is TESTED, not guessed: each hardware encoder encodes a few frames, and Blender is asked which Cycles devices
it can see. The result is cached in workspace/review/gpu.json and redone when the GPUs, drivers or Blender change.

What each vendor's driver gives the tools:
  NVIDIA  ffmpeg NVENC (h264/hevc/av1_nvenc) + CUDA decode; Blender Cycles CUDA (OptiX on RTX); whisper.cpp CUDA build.
  AMD     ffmpeg AMF (h264/hevc/av1_amf) via the Adrenalin driver; Blender Cycles HIP (Radeon RX 5000 and newer);
          whisper.cpp CPU (BLAS) build.
  Intel   ffmpeg Quick Sync (h264/hevc/av1_qsv) via the Intel graphics driver (oneVPL); Blender Cycles oneAPI (Arc GPUs);
          whisper.cpp CPU (BLAS) build.
  Any     Chrome (HyperFrames) uses the GPU through Direct3D with any vendor; ffmpeg can decode with d3d11va on all three.
"""
import json, os, subprocess, sys, time
from pathlib import Path

NOWIN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
VENDOR_IDS = {"10DE": "nvidia", "1002": "amd", "1022": "amd", "8086": "intel"}
ENCODERS = {"nvidia": ["h264_nvenc", "hevc_nvenc", "av1_nvenc"], "amd": ["h264_amf", "hevc_amf", "av1_amf"],
            "intel": ["h264_qsv", "hevc_qsv", "av1_qsv"]}
# fast settings for previews, and good settings when a final may use the hardware encoder
DRAFT_ARGS = {"h264_nvenc": ["-c:v", "h264_nvenc", "-preset", "p1", "-cq", "30"],
              "h264_amf": ["-c:v", "h264_amf", "-quality", "speed", "-rc", "cqp", "-qp_i", "30", "-qp_p", "30"],
              "h264_qsv": ["-c:v", "h264_qsv", "-preset", "veryfast", "-global_quality", "30"],
              "libx264": ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "30"]}
FINAL_ARGS = {"h264_nvenc": ["-c:v", "h264_nvenc", "-preset", "p6", "-rc", "vbr", "-cq", "19", "-b:v", "0"],
              "h264_amf": ["-c:v", "h264_amf", "-quality", "quality", "-rc", "cqp", "-qp_i", "18", "-qp_p", "20"],
              "h264_qsv": ["-c:v", "h264_qsv", "-preset", "slower", "-global_quality", "20"],
              "libx264": ["-c:v", "libx264", "-preset", "medium", "-crf", "17"]}
BLENDER_ORDER = {"nvidia": ["OPTIX", "CUDA"], "amd": ["HIP"], "intel": ["ONEAPI"]}
DRIVER_PAGES = {"nvidia": "https://www.nvidia.com/drivers", "amd": "https://www.amd.com/en/support/download/drivers.html",
                "intel": "https://www.intel.com/content/www/us/en/support/detect.html"}


def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=NOWIN)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, str(e)


def adapters():
    """[{name, vendor, driver, vram_gb}] from Windows (virtual/remote display adapters are skipped)"""
    ps = ("Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,PNPDeviceID,AdapterRAM | ConvertTo-Json -Compress")
    code, out = run(["powershell", "-NoProfile", "-Command", ps], 30)
    try: rows = json.loads(out.strip() or "[]")
    except Exception: rows = []
    if isinstance(rows, dict): rows = [rows]
    res = []
    for r in rows:
        pnp = (r.get("PNPDeviceID") or "").upper()
        ven = next((v for k, v in VENDOR_IDS.items() if f"VEN_{k}" in pnp), None)
        if not ven: continue
        res.append({"name": (r.get("Name") or "").strip(), "vendor": ven, "driver": r.get("DriverVersion") or "",
                    "vram_gb": round((r.get("AdapterRAM") or 0) / 2**30, 1)})
    return res


def encoder_test(enc):
    """None when it works, else ffmpeg's reason"""
    code, out = run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=640x360:r=30", "-frames:v", "10",
                   "-pix_fmt", "yuv420p", "-c:v", enc, "-f", "null", "-"], 40)
    if code == 0: return None
    lines = [l.split("] ", 1)[-1] for l in out.splitlines() if l.strip()]
    return " ".join(lines[:2])[:300] or "failed"


BLENDER_PROBE = r"""
import bpy, json
p = bpy.context.preferences.addons["cycles"].preferences
out = {}
for t in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
    try:
        p.compute_device_type = t
        p.refresh_devices()
        out[t] = [d.name for d in p.get_devices_for_type(t) if d.type != "CPU"]
    except Exception:
        pass
print("RRDEV" + json.dumps(out))
"""


def blender_devices(blender):
    if not blender: return {}
    code, out = run([blender, "-b", "--factory-startup", "--python-expr", BLENDER_PROBE], 120)
    line = next((l for l in out.splitlines() if l.startswith("RRDEV")), None)
    try: return {k: v for k, v in json.loads(line[5:]).items() if v} if line else {}
    except Exception: return {}


def detect(cache=None, blender=None, force=False):
    ad = adapters()
    key = json.dumps([[a["name"], a["driver"]] for a in ad] + [blender or ""])
    if cache and not force and Path(cache).exists():
        try:
            c = json.loads(Path(cache).read_text(encoding="utf-8"))
            if c.get("key") == key: return c
        except Exception: pass
    vendors = [v for v in ("nvidia", "amd", "intel") if any(a["vendor"] == v for a in ad)]
    tests = {e: encoder_test(e) for v in vendors for e in ENCODERS[v]}
    enc = {v: [e for e in ENCODERS[v] if tests[e] is None] for v in vendors}
    h264 = next((e for v in vendors for e in enc[v] if e.startswith("h264_")), None)
    bdev = blender_devices(blender)
    border = [t for v in vendors for t in BLENDER_ORDER[v]]
    if not any("RTX" in a["name"].upper() for a in ad): border = [t for t in border if t != "OPTIX"]   # OptiX only pays off on RTX
    cycles = next((t for t in border if bdev.get(t)), "CPU" if blender else None)
    notes = []
    for v in vendors:
        if not enc[v]:
            why = tests[ENCODERS[v][0]]
            notes.append(f"{v.upper()} GPU found but its hardware video encoder does not work ({why}). Update the graphics driver "
                         f"({DRIVER_PAGES[v]}); until then the CPU encoder (libx264) is used.")
    res = {"key": key, "checked": time.time(), "adapters": ad, "vendors": vendors, "encoders": enc,
           "draft_encoder": h264 or "libx264", "draft_args": DRAFT_ARGS[h264 or "libx264"],
           "final_hw_args": FINAL_ARGS.get(h264) if h264 else None,
           "decode": "cuda" if "nvidia" in vendors else ("d3d11va" if vendors else None),
           "blender": {"devices": bdev, "cycles_device": cycles} if blender else None,
           "whisper": "cuda" if "nvidia" in vendors else "cpu", "notes": notes}
    if cache:
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
        Path(cache).write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


def summary(g):
    """a few lines for prompts and the Settings panel"""
    if not g: return "GPU: not checked yet."
    if not g["adapters"]: return "GPU: none found (CPU only). Use libx264 and Blender on the CPU; keep 3D light."
    names = ", ".join(f"{a['name']} (driver {a['driver']})" for a in g["adapters"])
    lines = [f"GPU: {names}."]
    lines.append(f"Hardware video encoders that work: {', '.join(e for v in g['encoders'].values() for e in v) or 'none'}. "
                 f"Fast previews: `{' '.join(g['draft_args'])}`. Finals: libx264 `-crf 16-18` for the best quality"
                 + (f", or `{' '.join(g['final_hw_args'])}` when speed matters." if g.get("final_hw_args") else "."))
    if g.get("decode"): lines.append(f"Hardware decode: `-hwaccel {g['decode']}` (optional).")
    if g.get("blender"):
        d = g["blender"]["cycles_device"]
        lines.append(f"Blender Cycles device: {d}" + (f" (set `prefs.compute_device_type = '{d}'` and enable its devices, "
                     "scene.cycles.device = 'GPU')." if d != "CPU" else " (no supported GPU: use EEVEE or few samples)."))
    lines.append(f"Whisper runs on the {'GPU (CUDA)' if g['whisper'] == 'cuda' else 'CPU'}."
                 + ("" if g["whisper"] == "cuda" else " Prefer the small model for long files."))
    lines.append("HyperFrames: add `--gpu` to renders" if g["draft_encoder"] != "libx264" else "HyperFrames: render without --gpu")
    lines[-1] += " (Chrome uses the GPU through Direct3D on any vendor)."
    return "\n".join(lines + g.get("notes", []))


if __name__ == "__main__":
    import shutil
    here = Path(__file__).resolve().parent
    base = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Blender Foundation"
    found = sorted(base.glob("*/blender.exe"), reverse=True) if base.exists() else []
    bl = str(found[0]) if found else shutil.which("blender")
    g = detect(here.parent / "workspace" / "review" / "gpu.json", bl, force="--force" in sys.argv)
    print(json.dumps(g, indent=1) if "--json" in sys.argv else summary(g))
