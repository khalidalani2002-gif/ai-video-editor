"""Review Room analysis + processing helpers (standard library + ffmpeg + whisper.cpp).

Scene cuts, measured checks (loudness, black and flash frames), automatic colour correction (per shot),
colour matching to a reference frame, LUT looks, speech-to-text with word timings, frame images for notes.
"""
import json, math, os, re, socket, subprocess, tempfile, threading, time, urllib.request, uuid
from pathlib import Path

NOWIN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
APP = Path(__file__).resolve().parent
LUTS = APP / "luts"                                          # the app's colour looks (.cube); ffmpeg runs with cwd = app/


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, creationflags=NOWIN, **kw)


# ------------------------------------------------------------------ scene cuts
def scene_cuts(p: Path, threshold=12.0):
    """times (s) where a new shot starts"""
    r = run(["ffmpeg", "-hide_banner", "-v", "info", "-i", str(p), "-an", "-vf", f"scale=240:-2,scdet=threshold={threshold}",
             "-f", "null", "-"], text=True, encoding="utf-8", errors="replace")
    return [round(float(x), 4) for x in re.findall(r"lavfi\.scd\.time:\s*([0-9.]+)", r.stderr)]


def segments(duration, cuts, min_len=0.8, max_n=40):
    """shots as (start, end); very short shots are merged into their neighbour"""
    edges = [0.0] + [c for c in cuts if 0 < c < duration] + [duration]
    segs = []
    for a, b in zip(edges, edges[1:]):
        if segs and (b - a < min_len or segs[-1][1] - segs[-1][0] < min_len): segs[-1] = (segs[-1][0], b)
        else: segs.append((a, b))
    return segs if len(segs) <= max_n else [(0.0, duration)]


# ------------------------------------------------------------------ pixel statistics
def sample_rgb(p: Path, a, b, n=5, w=96, at=None):
    """raw RGB bytes of n frames spread over [a, b] (or the one frame at `at`), scaled to w px wide"""
    if at is not None:
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{at:.4f}", "-i", str(p), "-frames:v", "1", "-vf", f"scale={w}:-2",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    else:
        L = max(0.05, b - a - 0.04)
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{a + 0.02:.4f}", "-t", f"{L:.4f}", "-i", str(p),
               "-vf", f"fps={n / L:.5f},scale={w}:-2", "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    return run(cmd).stdout


def channel_stats(raw: bytes):
    """per channel: histogram percentiles, mean, std"""
    out = []
    for c in range(3):
        ch = raw[c::3]
        if not ch: return None
        h = [0] * 256
        for v in ch: h[v] += 1
        n = len(ch); mean = sum(i * k for i, k in enumerate(h)) / n
        sd = math.sqrt(max(1e-6, sum(k * (i - mean) ** 2 for i, k in enumerate(h)) / n))

        def pct(q):
            acc, lim = 0, q * n
            for i, k in enumerate(h):
                acc += k
                if acc >= lim: return i
            return 255
        out.append({"lo": pct(0.004), "hi": pct(0.996), "mean": mean, "sd": sd})
    return out


def _expr(core, s):
    """blend a per-value correction with the original by strength s"""
    return f"clip(val+{s:.3f}*(({core})-val),0,255)"


def _lut(exprs, a=None, b=None):
    en = f":enable='between(t,{a:.4f},{b:.4f})'" if a is not None else ""
    return f"lutrgb=r='{exprs[0]}':g='{exprs[1]}':b='{exprs[2]}'{en}"


def auto_color_filter(p: Path, duration, cuts, strength=0.6):
    """per shot: per-channel black/white points (removes casts + flat contrast) and grey-world midtone balance"""
    segs = segments(duration, cuts)
    parts, report = [], []
    for a, b in segs:
        st = channel_stats(sample_rgb(p, a, b))
        if not st: continue
        lo = [min(s["lo"], 40) for s in st]; hi = [max(s["hi"], 190) for s in st]
        exprs, mids = [], []
        for c in range(3):
            D = max(40, hi[c] - lo[c]); D = max(D, 255 / 1.6)       # never more than 1.6x gain
            m = min(0.95, max(0.05, (st[c]["mean"] - lo[c]) / D)); mids.append((lo[c], D, m))
        T = sum(m for _, _, m in mids) / 3
        for L, D, m in mids:
            g = min(1.25, max(0.8, math.log(T) / math.log(m)))
            exprs.append(_expr(f"255*pow(clip((val-{L})/{D:.2f},0,1),{g:.4f})", strength))
        parts.append(_lut(exprs, a if len(segs) > 1 else None, b if len(segs) > 1 else None))
        report.append(f"{a:5.2f}-{b:5.2f}s  black {lo}  white {hi}")
    return ",".join(parts + ["format=yuv420p"]), report


def match_color_filter(p: Path, duration, cuts, ref: Path, ref_t, strength=0.7):
    """per shot: move each channel's mean/contrast toward the reference frame's"""
    rs = channel_stats(sample_rgb(ref, 0, 0, at=ref_t, w=192))
    if not rs: raise RuntimeError("could not read the reference frame")
    segs = segments(duration, cuts)
    parts, report = [], []
    for a, b in segs:
        st = channel_stats(sample_rgb(p, a, b))
        if not st: continue
        exprs = []
        for c in range(3):
            k = min(1.4, max(0.7, rs[c]["sd"] / st[c]["sd"]))
            exprs.append(_expr(f"(val-{st[c]['mean']:.2f})*{k:.4f}+{rs[c]['mean']:.2f}", strength))
        parts.append(_lut(exprs, a if len(segs) > 1 else None, b if len(segs) > 1 else None))
        report.append(f"{a:5.2f}-{b:5.2f}s  mean {[round(s['mean']) for s in st]} -> {[round(s['mean']) for s in rs]}")
    return ",".join(parts + ["format=yuv420p"]), report


def luts():
    return sorted(x.stem for x in LUTS.glob("*.cube")) if LUTS.exists() else []


def look_filter(lut, strength=1.0):
    rel = f"luts/{lut}.cube"                                        # relative: ffmpeg runs with cwd = app/ (no drive colon)
    if strength >= 0.99: return f"lut3d='{rel}',format=yuv420p"
    return (f"split[a][b];[b]lut3d='{rel}'[c];[a][c]blend=all_mode=normal:all_opacity={strength:.3f},format=yuv420p")


def look_preview(p: Path, t, lut, out: Path, h=320):
    vf = f"scale=-2:{h}" + (f",lut3d='luts/{lut}.cube'" if lut else "")
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.4f}", "-i", str(p), "-frames:v", "1", "-vf", vf, "-q:v", "4", str(out)], cwd=str(APP))
    return out if out.exists() else None


def render_filtered(p: Path, vf: str, out: Path, complex_graph=False):
    """re-encode with a filter, audio copied; high quality"""
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(p)]
    cmd += (["-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-map", "0:a?"] if complex_graph else ["-vf", vf, "-map", "0:v", "-map", "0:a?"])
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(out)]
    r = run(cmd, cwd=str(APP), text=True, encoding="utf-8", errors="replace")
    if r.returncode or not out.exists(): raise RuntimeError((r.stderr or "ffmpeg failed")[-800:])
    return out


# ------------------------------------------------------------------ speech
def whisper_bin():
    p = os.environ.get("HYPERFRAMES_WHISPER_PATH") or str(Path(os.environ.get("LOCALAPPDATA", "")) / "whisper.cpp-cuda/Release/whisper-cli.exe")
    return p if Path(p).exists() else None


def model_path(name):
    p = Path.home() / ".cache/hyperframes/whisper/models" / f"ggml-{name}.bin"
    return p if p.exists() else None


def whisper_words(src: Path, language="auto", model="large-v3-turbo", gpu=True, words=True):
    """[{text, start, end}] (words=True) or plain text; any audio/video input"""
    exe, mp = whisper_bin(), model_path(model) or model_path("medium") or model_path("small")
    if not exe or not mp: raise RuntimeError("whisper.cpp or its model is missing (run tools/setup_windows.ps1)")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        to_wav(src, wav)
        base = Path(tmp) / "w"
        cmd = [exe, "-m", str(mp), "-f", str(wav), "-ojf", "-of", str(base), "-l", language, "-np"]
        if words: cmd += ["-ml", "1", "-sow"]
        if not gpu: cmd += ["-ng", "-t", str(max(2, (os.cpu_count() or 4) - 1))]
        run(cmd)
        jp = base.with_suffix(".json")
        if not jp.exists(): raise RuntimeError("whisper failed")
        j = json.loads(jp.read_text(encoding="utf-8", errors="replace"))
    out = []
    for seg in j.get("transcription", []):
        if not words:
            out.append(seg.get("text", "").strip()); continue
        for tok in seg.get("tokens", []):
            t = tok.get("text", "")
            if not t.strip() or re.fullmatch(r"\[_?[A-Z_]+\d*_?\]|<\|.*\|>", t.strip()): continue
            s = tok.get("offsets", {}).get("from", 0) / 1000.0; e = tok.get("offsets", {}).get("to", 0) / 1000.0
            if t.startswith(" ") or not out: out.append({"text": t.strip(), "start": round(s, 3), "end": round(e, 3)})
            else: out[-1]["text"] += t; out[-1]["end"] = round(e, 3)
    if not words: return " ".join(x for x in out if x)
    out = [w for w in out if w["text"]]
    # music-only audio makes whisper invent stretched words ("see you next time"): real words are short
    if out and sum(w["end"] - w["start"] > 2.0 for w in out) > len(out) / 3: return []
    return [w for w in out if w["end"] - w["start"] <= 2.0]


def to_wav(src: Path, dst: Path):
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dst)])
    if not dst.exists(): raise RuntimeError("could not read the audio")
    return dst


class WhisperDaemon:
    """whisper-server with the model kept loaded, so spoken notes come back in a second or two instead of ~40 s.
    Started on demand, stopped when idle or when a GPU job starts (one GPU job at a time)."""

    def __init__(self, port=8178, model="large-v3-turbo"):
        self.port, self.model, self.proc, self.last = port, model, None, 0.0
        self.lock = threading.Lock()

    def exe(self):
        w = whisper_bin()
        p = Path(w).with_name("whisper-server.exe") if w else None
        return p if p and p.exists() else None

    def running(self): return self.proc is not None and self.proc.poll() is None

    def start(self):
        with self.lock:
            self.last = time.time()
            if self.running(): return True
            exe, mp = self.exe(), model_path(self.model)
            if not exe or not mp: return False
            self.proc = subprocess.Popen([str(exe), "-m", str(mp), "--host", "127.0.0.1", "--port", str(self.port), "-l", "auto"],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NOWIN)
            for _ in range(360):                                     # model load: up to 90 s on a busy disk
                if self.proc.poll() is not None: return False
                try:
                    socket.create_connection(("127.0.0.1", self.port), 0.5).close(); return True
                except OSError: time.sleep(0.25)
            return False

    def stop(self):
        with self.lock:
            if self.running(): self.proc.terminate()
            self.proc = None

    def idle_check(self, limit=600):
        if self.running() and time.time() - self.last > limit: self.stop()

    def transcribe(self, wav: Path, language="auto"):
        if not self.start(): raise RuntimeError("whisper-server did not start")
        bnd = "----rr" + uuid.uuid4().hex
        parts = []
        for k, v in (("response_format", "json"), ("language", language), ("temperature", "0.0")):
            parts.append(f'--{bnd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f'--{bnd}\r\nContent-Disposition: form-data; name="file"; filename="a.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
                     + wav.read_bytes() + b"\r\n")
        body = b"".join(parts) + f"--{bnd}--\r\n".encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/inference", body, {"Content-Type": f"multipart/form-data; boundary={bnd}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            j = json.loads(r.read().decode("utf-8", "replace"))
        self.last = time.time()
        return " ".join((j.get("text") or "").split())


# ------------------------------------------------------------------ frame image for a note made by the app or by Claude
def frame_png(p: Path, t, out: Path, x=None, y=None, box=None):
    vf = []
    if box:
        a, b, c, d = box
        vf.append(f"drawbox=x=iw*{a:.4f}:y=ih*{b:.4f}:w=iw*{c - a:.4f}:h=ih*{d - b:.4f}:color=white@0.9:t=10,"
                  f"drawbox=x=iw*{a:.4f}:y=ih*{b:.4f}:w=iw*{c - a:.4f}:h=ih*{d - b:.4f}:color=0xff2d43:t=5")
    elif x is not None and y is not None:
        vf.append(f"drawbox=x=iw*{x:.4f}-iw/30:y=ih*{y:.4f}-iw/30:w=iw/15:h=iw/15:color=white@0.9:t=8,"
                  f"drawbox=x=iw*{x:.4f}-iw/30:y=ih*{y:.4f}-iw/30:w=iw/15:h=iw/15:color=0xff2d43:t=4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, t):.4f}", "-i", str(p), "-frames:v", "1"]
    if vf: cmd += ["-vf", ",".join(vf)]
    run(cmd + [str(out)])
    return out.exists()
