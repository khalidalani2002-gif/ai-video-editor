"""Example images for the edit (footage) and animation (2D) styles: HTML/CSS stills photographed with headless Chrome,
the same way HyperFrames builds video frames. Footage frames come from the app's Default assets.

    python make_2d.py <ReviewRoom folder> <out folder> [style ids...]
"""
import json, os, subprocess, sys
from pathlib import Path

ROOT, OUT = Path(sys.argv[1]), Path(sys.argv[2])
ONLY = set(sys.argv[3:])
HERE = Path(__file__).resolve().parent
DA = ROOT / "workspace" / "assets" / "Default assets"
WORK = HERE / "html"; FR = WORK / "frames"
for d in (OUT, WORK, FR): d.mkdir(parents=True, exist_ok=True)
CHROME = next((p for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe", os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe") if os.path.exists(p)), None)
NOWIN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
F = lambda *p: (DA / "Fonts" / Path(*p)).as_uri()
FONTS = f"""
@font-face {{ font-family: Anton; src: url('{F("Latin", "anton", "Anton-Regular.ttf")}'); }}
@font-face {{ font-family: Bebas; src: url('{F("Latin", "bebasneue", "BebasNeue-Regular.ttf")}'); }}
@font-face {{ font-family: Playfair; src: url('{F("Latin", "playfairdisplay", "PlayfairDisplay[wght].ttf")}'); font-weight: 400 900; }}
@font-face {{ font-family: Grotesk; src: url('{F("Latin", "spacegrotesk", "SpaceGrotesk[wght].ttf")}'); font-weight: 300 700; }}
@font-face {{ font-family: Marker; src: url('{F("Latin", "permanentmarker", "PermanentMarker-400.ttf")}'); }}
@font-face {{ font-family: Caveat; src: url('{F("Latin", "caveat", "Caveat-600.ttf")}'); }}
@font-face {{ font-family: Archivo; src: url('{F("Latin", "archivoblack", "ArchivoBlack-Regular.ttf")}'); }}
@font-face {{ font-family: Orbitron; src: url('{F("Latin", "orbitron", "Orbitron-600.ttf")}'); }}
@font-face {{ font-family: Tajawal; src: url('{F("Arabic", "tajawal", "Tajawal-Black.ttf")}'); }}
"""
BASE = "*{box-sizing:border-box;margin:0;padding:0} html,body{width:960px;height:540px;overflow:hidden} body{position:relative;font-family:'Segoe UI',sans-serif}"


def frame(sid, rel, t):
    out = FR / f"{sid}.jpg"
    if not out.exists():
        src = DA / rel
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(src), "-frames:v", "1",
                        "-vf", "scale=960:540:force_original_aspect_ratio=increase,crop=960:540", "-q:v", "3", str(out)],
                       creationflags=NOWIN)
    return out.as_uri()


def first_media(folder):
    for p in sorted((DA / folder).rglob("*")):
        if p.suffix.lower() in (".mp4", ".webm", ".mov"): return p.relative_to(DA)
    return None


def iraq_svg(w=520, h=470):
    gj = next((p for p in (DA / "Maps").rglob("irq-adm1.geojson")), None)
    if not gj: return "", {}
    data = json.loads(gj.read_text(encoding="utf-8"))
    rings = []
    for f in data["features"]:
        g = f["geometry"]; polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys: rings.append(poly[0])
    xs = [p[0] for r in rings for p in r]; ys = [p[1] for r in rings for p in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    sc = min((w - 20) / (x1 - x0), (h - 20) / (y1 - y0))
    P = lambda lon, lat: (10 + (lon - x0) * sc, 10 + (y1 - lat) * sc)
    paths = "".join('<path d="M' + "L".join(f"{P(*pt)[0]:.1f},{P(*pt)[1]:.1f}" for pt in r[::2]) + 'Z"/>' for r in rings)
    cities = {"Baghdad": (44.36, 33.31), "Basra": (47.78, 30.51), "Erbil": (44.01, 36.19), "Mosul": (43.13, 36.34)}
    return paths, {k: P(*v) for k, v in cities.items()}


def page(body, css=""):
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{FONTS}{BASE}{css}</style></head><body>{body}</body></html>"


S = {}

# ------------------------------------------------------------------ edit styles (on real footage)
S["cinematic"] = lambda: page(f"""<img class=bg src="{frame('cinematic', 'Footage/Background/51445-sunset-behind-the-skyline-on-the-beach-over-the-sea.mp4', 4)}">
<div class=bar></div><div class="bar b"></div><div class=t><small>A FILM BY THE SEA</small>Golden Hours</div>""",
 ".bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:contrast(1.12) saturate(1.25) sepia(.18) hue-rotate(-8deg)}"
 ".bar{position:absolute;left:0;right:0;top:0;height:66px;background:#000}.bar.b{top:auto;bottom:0}"
 ".t{position:absolute;left:0;right:0;bottom:96px;text-align:center;color:#f4e9d8;font:italic 600 54px Playfair;letter-spacing:.06em;text-shadow:0 2px 18px #0009}"
 ".t small{display:block;font:500 13px Grotesk;letter-spacing:.5em;margin-bottom:8px;opacity:.85}")

S["reels"] = lambda: page(f"""<img class=bg src="{frame('reels', 'Footage/People/4840-woman-during-a-sunset-on-a-rooftop.mp4', 4)}">
<div class=ph><img src="{frame('reels', 'Footage/People/4840-woman-during-a-sunset-on-a-rooftop.mp4', 4)}"><div class=cap>WAIT FOR <b>IT</b>…</div>
<div class=ui><i>♥</i><i>💬</i><i>↗</i></div></div>""",
 ".bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:blur(18px) brightness(.55)}"
 ".ph{position:absolute;left:50%;top:22px;width:278px;height:496px;margin-left:-139px;border-radius:26px;overflow:hidden;box-shadow:0 20px 60px #000a;border:6px solid #111}"
 ".ph img{width:100%;height:100%;object-fit:cover;transform:scale(1.35);transform-origin:40% 40%}"
 ".cap{position:absolute;left:0;right:0;top:46%;text-align:center;font:46px Anton;color:#fff;-webkit-text-stroke:2px #000;paint-order:stroke;transform:rotate(-4deg)}"
 ".cap b{color:#ffd60a;font-weight:400}.ui{position:absolute;right:10px;bottom:70px;display:flex;flex-direction:column;gap:16px;font-size:24px;color:#fff}")

S["minimal"] = lambda: page(f"""<img class=bg src="{frame('minimal', 'Footage/Background/1564-white-sand-beach-background.mp4', 3)}">
<div class=t>still.<small>summer collection</small></div>""",
 ".bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:saturate(.75) brightness(1.08)}"
 ".t{position:absolute;left:64px;bottom:64px;color:#1c1c1c;font:300 56px Grotesk;letter-spacing:-.02em}.t small{display:block;font:400 14px Grotesk;letter-spacing:.3em;margin-top:6px;opacity:.7}")

S["corporate"] = lambda: page(f"""<img class=bg src="{frame('corporate', 'Footage/Business/4809-business-people-at-work-meeting.mp4', 3)}">
<div class=lt><div class=n>Sara Al-Hassan</div><div class=r>Head of Operations</div></div><div class=logo>◆ NORTHWIND</div>""",
 ".bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}"
 ".lt{position:absolute;left:56px;bottom:70px;background:#fff;border-left:8px solid #0b4f9c;padding:12px 22px 12px 18px;box-shadow:0 8px 30px #0005}"
 ".n{font:700 26px 'Segoe UI';color:#0b2340}.r{font:400 15px 'Segoe UI';color:#0b4f9c;margin-top:2px}"
 ".logo{position:absolute;right:34px;top:28px;color:#fff;font:700 16px 'Segoe UI';letter-spacing:.2em;background:#0b4f9ccc;padding:6px 12px}")

S["documentary"] = lambda: page(f"""<img class=bg src="{frame('documentary', 'Footage/Business/308-man-working-on-his-laptop.mp4', 4)}">
<div class=lt>KARIM, 34<br><span>software engineer · Baghdad</span></div><div class=sub>"I started with nothing but a laptop and an idea."</div>""",
 ".bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:saturate(.8) contrast(.95) sepia(.08)}"
 ".lt{position:absolute;left:52px;top:52px;color:#fff;font:600 18px Grotesk;letter-spacing:.12em;text-shadow:0 1px 8px #000a}.lt span{font-weight:400;font-size:13px;letter-spacing:.05em;opacity:.85}"
 ".sub{position:absolute;left:0;right:0;bottom:44px;text-align:center;color:#fff;font:italic 22px Georgia;text-shadow:0 2px 6px #000}")

S["vlog"] = lambda: page(f"""<img class=bg src="{frame('vlog', 'Footage/City/4231-pedestrian-walk-in-tokyo.mp4', 4)}">
<div class=cap><span>day 3 in</span> <b>TOKYO</b> 🍜</div><div class=st>📍 Shibuya</div>""",
 ".bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:saturate(1.2) brightness(1.05)}"
 ".cap{position:absolute;left:50%;bottom:70px;transform:translateX(-50%) rotate(-2deg);background:#fff;color:#111;padding:10px 20px;border-radius:14px;font:800 30px 'Segoe UI';white-space:nowrap;box-shadow:0 6px 0 #ff9f1c}"
 ".cap b{color:#ff4f00}.st{position:absolute;left:40px;top:40px;background:#2ec4b6;color:#fff;font:700 18px 'Segoe UI';padding:6px 14px;border-radius:99px;transform:rotate(-6deg)}")


def meme():
    rel = first_media("Arabic/Memes/Classics") or first_media("Arabic/Memes")
    src = frame("meme", rel, 1) if rel else ""
    return page(f"""<img class=bg src="{src}"><div class=top>لمن تشوف الفاتورة</div><div class=bot>وتگول: منو طلب كل هذا؟ 😂</div><div class=zoom></div>""",
                ".bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform:scale(1.25)}"
                ".top,.bot{position:absolute;left:0;right:0;text-align:center;direction:rtl;font:48px Tajawal;color:#fff;-webkit-text-stroke:3px #000;paint-order:stroke}"
                ".top{top:26px;color:#ffde00}.bot{bottom:30px}.zoom{position:absolute;inset:0;box-shadow:inset 0 0 160px #e4002b88}")
S["meme"] = meme

S["tutorial"] = lambda: page(f"""<img class=bg src="{frame('tutorial', 'Footage/Business/1781-typing-on-a-laptop-close-up.mp4', 3)}">
<div class=hl></div><div class=step><b>2</b> Open <u>Settings</u> → <u>Export</u></div><div class=cur></div>""",
 ".bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform:scale(1.4);transform-origin:55% 45%;filter:brightness(.8)}"
 ".hl{position:absolute;left:470px;top:170px;width:230px;height:120px;border:3px solid #3fb950;border-radius:10px;box-shadow:0 0 0 2000px #0008}"
 ".step{position:absolute;left:40px;top:40px;background:#0e1117;color:#e6edf3;font:600 22px 'Segoe UI';padding:10px 18px;border-radius:10px;border:1px solid #30363d}"
 ".step b{background:#3fb950;color:#0e1117;border-radius:6px;padding:0 9px;margin-right:8px}.step u{text-decoration:none;color:#58a6ff}"
 ".cur{position:absolute;left:640px;top:250px;width:0;height:0;border-left:14px solid #fff;border-top:10px solid transparent;border-bottom:22px solid transparent;transform:rotate(-20deg);filter:drop-shadow(0 2px 3px #000)}")

S["trailer"] = lambda: page(f"""<img class=bg src="{frame('trailer', 'Footage/Background/28897-slowly-approaching-a-clock-on-a-black-background.mp4', 4)}">
<div class=t>TIME<br>IS RUNNING<br>OUT</div><div class=d>THIS WINTER</div>""",
 ".bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:contrast(1.3) brightness(.65) saturate(.4) sepia(.3) hue-rotate(-30deg)}"
 ".t{position:absolute;left:0;right:0;top:120px;text-align:center;color:#eee;font:86px/0.95 Bebas;letter-spacing:.08em;text-shadow:0 0 30px #b3000088}"
 ".d{position:absolute;left:0;right:0;bottom:46px;text-align:center;color:#b30000;font:24px Bebas;letter-spacing:.6em}")


def beforeafter():
    src = frame("beforeafter", "Footage/People/4629-backlit-woman-walking-at-sunset.mp4", 3)
    return page(f"""<img class="bg b" src="{src}"><div class=after><img class=bg src="{src}"></div><div class=line></div>
<div class="lab l">BEFORE</div><div class="lab r">AFTER</div>""",
                ".bg{position:absolute;inset:0;width:960px;height:540px;object-fit:cover}.b{filter:saturate(.35) contrast(.75) brightness(.95)}"
                ".after{position:absolute;left:480px;top:0;bottom:0;right:0;overflow:hidden}.after .bg{left:-480px;filter:saturate(1.35) contrast(1.15) sepia(.12)}"
                ".line{position:absolute;left:478px;top:0;bottom:0;width:4px;background:#fff;box-shadow:0 0 12px #000a}"
                ".lab{position:absolute;top:30px;font:800 16px 'Segoe UI';letter-spacing:.25em;color:#fff;background:#0009;padding:6px 12px}.l{left:30px}.r{right:30px;background:#22c55e}")
S["beforeafter"] = beforeafter

S["retro"] = lambda: page(f"""<img class=bg src="{frame('retro', 'Footage/City/4332-times-square-during-a-rainy-night.mp4', 3)}">
<img class="bg r" src="{frame('retro', 'Footage/City/4332-times-square-during-a-rainy-night.mp4', 3)}"><div class=scan></div>
<div class=osd>PLAY ▶<br><span>SP 0:12:47</span></div><div class=date>NOV 12 1989</div>""",
 ".bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:saturate(1.5) contrast(1.1) blur(.6px)}"
 ".r{mix-blend-mode:screen;opacity:.55;transform:translateX(5px);filter:saturate(2) hue-rotate(160deg) blur(1px)}"
 ".scan{position:absolute;inset:0;background:repeating-linear-gradient(0deg,#0003 0 2px,transparent 2px 4px)}"
 ".osd{position:absolute;left:40px;top:34px;color:#fff;font:30px 'Consolas';text-shadow:2px 2px 0 #00f0ff,-2px -1px 0 #ff6ec7}.osd span{font-size:20px}"
 ".date{position:absolute;right:40px;bottom:34px;color:#fff;font:24px Consolas;text-shadow:2px 2px 0 #ff6ec7}")

S["luxury"] = lambda: page(f"""<img class=bg src="{frame('luxury', 'Footage/Business/3653-hands-of-a-wrist-watch.mp4', 3)}">
<div class=v></div><div class=t>ÉTERNEL<small>— crafted for a lifetime —</small></div>""",
 ".bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:saturate(.6) contrast(1.2) brightness(.7) sepia(.35)}"
 ".v{position:absolute;inset:0;background:radial-gradient(ellipse at 40% 45%,transparent 30%,#000d 85%)}"
 ".t{position:absolute;right:70px;top:190px;text-align:right;color:#c9a227;font:400 58px Playfair;letter-spacing:.32em;padding-top:8px}"
 ".t small{display:block;color:#f5ecd7;font:italic 16px Playfair;letter-spacing:.18em;margin-top:10px}")

S["clinical"] = lambda: page(f"""<img class=bg src="{(OUT / 'medical3d.png').as_uri()}">
<div class=p style="left:56px;top:70px"><b>01</b> Intraoral scan<span>accuracy 20 µm</span></div>
<div class=p style="right:56px;top:300px"><b>02</b> Digital model<span>ready in 3 minutes</span></div>
<div class=ln style="left:250px;top:110px;width:150px;transform:rotate(25deg)"></div>""",
 ".bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:brightness(.97) contrast(1.05)}"
 ".p{position:absolute;background:#ffffffee;color:#0b2a55;font:700 20px 'Segoe UI';padding:10px 16px;border-radius:10px;box-shadow:0 8px 24px #0003}"
 ".p b{color:#1e6fd9;margin-right:8px}.p span{display:block;font:400 13px 'Segoe UI';color:#557}.ln{position:absolute;height:2px;background:#7fd1e8;transform-origin:left}")

# ------------------------------------------------------------------ animation (2D motion graphics)
S["kinetic"] = lambda: page("""<div class=w1>MAKE</div><div class=w2>EVERY</div><div class=w3>WORD</div><div class=w4>MOVE.</div><div class=blk></div>""",
 "body{background:#141414}.blk{position:absolute;left:520px;top:300px;width:300px;height:110px;background:#ff4d00;z-index:0}"
 "div[class^=w]{position:absolute;color:#f0f0f0;font:120px/1 Archivo;z-index:1;letter-spacing:-.03em}"
 ".w1{left:60px;top:40px}.w2{left:60px;top:160px;color:transparent;-webkit-text-stroke:2px #f0f0f0}.w3{left:250px;top:280px;transform:rotate(-8deg)}"
 ".w4{left:540px;top:410px;font-size:90px;color:#ff4d00}")

S["explainer"] = lambda: page("""<div class=row>
<div class=st><div class="ic a">📱</div><b>1. Book</b><span>pick a time in the app</span></div><i>➜</i>
<div class=st><div class="ic b">🦷</div><b>2. Scan</b><span>3D scan in 3 minutes</span></div><i>➜</i>
<div class=st><div class="ic c">✨</div><b>3. Smile</b><span>your crown, same day</span></div></div>
<div class=t>How it works</div>""",
 "body{background:#f7f7fb}.t{position:absolute;top:56px;left:0;right:0;text-align:center;font:700 40px Grotesk;color:#2b2b55}"
 ".row{position:absolute;top:170px;left:0;right:0;display:flex;justify-content:center;align-items:center;gap:22px}"
 ".st{width:220px;text-align:center;font:15px 'Segoe UI';color:#555}.st b{display:block;font:700 24px Grotesk;color:#2b2b55;margin:14px 0 4px}"
 ".ic{width:150px;height:150px;margin:0 auto;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:68px}"
 ".a{background:#5b5bd6}.b{background:#ffc857}.c{background:#ff7aa2}i{font-style:normal;font-size:38px;color:#5b5bd6;margin-top:-60px}")


def isometric():
    def cube(x, y, h, top, left, right):
        return (f'<g transform="translate({x},{y})"><polygon points="0,-{h} 60,{-h + 34} 0,{-h + 68} -60,{-h + 34}" fill="{top}"/>'
                f'<polygon points="-60,{-h + 34} 0,{-h + 68} 0,68 -60,34" fill="{left}"/><polygon points="60,{-h + 34} 0,{-h + 68} 0,68 60,34" fill="{right}"/></g>')
    blocks = [(380, 300, 160, "#a5b4fc", "#6366f1", "#4338ca"), (500, 360, 90, "#fda4af", "#f43f5e", "#be123c"), (260, 360, 60, "#fde68a", "#f59e0b", "#b45309"),
              (380, 420, 40, "#86efac", "#22c55e", "#15803d"), (620, 300, 120, "#93c5fd", "#3b82f6", "#1d4ed8"), (500, 240, 200, "#c4b5fd", "#8b5cf6", "#6d28d9")]
    svg = "".join(cube(*b) for b in sorted(blocks, key=lambda b: b[1]))
    return page(f'<svg width=960 height=540><rect width=960 height=540 fill="#eef2ff"/>'
                f'<polygon points="440,170 900,436 440,700 -20,436" fill="#e0e7ff"/>{svg}</svg><div class=t>Your city,<br>connected.</div>',
                ".t{position:absolute;left:56px;top:60px;font:700 38px/1.1 Grotesk;color:#312e81}")
S["isometric"] = isometric

S["dataviz"] = lambda: page("""<div class=k><b>+248%</b><span>growth in bookings, 2026</span></div>
<div class=ch>""" + "".join(f'<div class=bar style="height:{h}px"><span>{m}</span></div>' for h, m in ((60, "Jan"), (85, "Feb"), (78, "Mar"), (120, "Apr"), (150, "May"), (210, "Jun"), (290, "Jul"))) + """</div>
<svg class=ln width=470 height=300><polyline points="10,260 80,230 150,238 220,190 290,150 360,90 450,20" fill=none stroke="#00e5a0" stroke-width=4/><circle cx=450 cy=20 r=8 fill="#00e5a0"/></svg>""",
 "body{background:#0f1220;color:#e8ebf5}.k{position:absolute;left:60px;top:80px}.k b{display:block;font:96px Bebas;color:#00e5a0;line-height:1}"
 ".k span{font:16px Grotesk;color:#9aa3c0}.ch{position:absolute;right:70px;bottom:70px;height:320px;display:flex;align-items:flex-end;gap:16px}"
 ".bar{width:48px;background:linear-gradient(#6c7cff,#3b46b8);border-radius:6px 6px 0 0;position:relative}.bar span{position:absolute;bottom:-24px;left:0;right:0;text-align:center;font:12px Grotesk;color:#9aa3c0}"
 ".ln{position:absolute;right:60px;bottom:70px}")


def mapanim():
    paths, c = iraq_svg()
    arcs = ""
    if c:
        b = c["Baghdad"]
        for k in ("Basra", "Erbil", "Mosul"):
            x, y = c[k]; mx, my = (b[0] + x) / 2, (b[1] + y) / 2 - 60
            arcs += f'<path d="M{b[0]:.0f},{b[1]:.0f} Q{mx:.0f},{my:.0f} {x:.0f},{y:.0f}" fill=none stroke="#ffd166" stroke-width=3 stroke-dasharray="8 6"/>'
        arcs += "".join(f'<circle cx={x:.0f} cy={y:.0f} r={10 if k == "Baghdad" else 6} fill="{"#ef476f" if k == "Baghdad" else "#ffd166"}"/>'
                        f'<text x={x + 12:.0f} y={y + 5:.0f} fill="#fff" font-family="Grotesk" font-size=16 font-weight=600>{k}</text>' for k, (x, y) in c.items())
    return page(f'<svg class=m width=520 height=470><g fill="#1b4965" stroke="#62b6cb" stroke-width=1>{paths}</g>{arcs}</svg>'
                '<div class=t>4 cities.<br><span>One network.</span></div>',
                "body{background:radial-gradient(circle at 70% 50%,#13315c,#0b132b)}.m{position:absolute;right:60px;top:35px}"
                ".t{position:absolute;left:60px;top:170px;color:#fff;font:700 50px/1.05 Grotesk}.t span{color:#ffd166}")
S["map"] = mapanim

S["uimock"] = lambda: page("""<div class=ph><div class=hd>Good morning, Ali ☀️</div>
<div class=card style="background:#6366f1"><small>Next appointment</small><b>Tue · 10:30</b></div>
<div class=row><div class=mini>📅<b>Book</b></div><div class=mini>💳<b>Pay</b></div><div class=mini>📄<b>Records</b></div></div>
<div class=card2>Your scan is ready ✓</div><div class=tap></div></div><div class=t>Book in<br><b>two taps.</b></div>""",
 "body{background:linear-gradient(135deg,#eef2ff,#fce7f3)}.ph{position:absolute;left:520px;top:24px;width:260px;height:520px;background:#fff;border-radius:34px;border:8px solid #111;padding:22px 16px;box-shadow:0 30px 60px #3b306655}"
 ".hd{font:700 17px Grotesk;color:#111;margin-bottom:14px}.card{color:#fff;border-radius:16px;padding:16px}.card small{opacity:.8}.card b{display:block;font:700 26px Grotesk}"
 ".row{display:flex;gap:8px;margin:14px 0}.mini{flex:1;background:#f4f4f7;border-radius:14px;text-align:center;padding:14px 0;font-size:22px}.mini b{display:block;font:600 12px 'Segoe UI';margin-top:4px}"
 ".card2{background:#dcfce7;color:#166534;border-radius:14px;padding:14px;font:600 14px 'Segoe UI'}"
 ".tap{position:absolute;left:52px;top:205px;width:46px;height:46px;border-radius:50%;background:#6366f155;box-shadow:0 0 0 12px #6366f122}"
 ".t{position:absolute;left:80px;top:180px;font:400 54px/1.05 Grotesk;color:#1e1b4b}.t b{font-weight:700;color:#6366f1}")

S["paper"] = lambda: page("""<div class=sun></div><div class="l l1"></div><div class="l l2"></div><div class="l l3"></div><div class="l l4"></div>
<div class=t>Into the<br>wild</div>""",
 "body{background:#fde2c4}.sun{position:absolute;left:600px;top:70px;width:150px;height:150px;border-radius:50%;background:#f4845f;box-shadow:0 8px 0 #0001}"
 ".l{position:absolute;left:-40px;right:-40px;bottom:0;filter:drop-shadow(0 -6px 6px #0003)}"
 ".l1{height:330px;background:#f7b267;clip-path:polygon(0 40%,15% 20%,30% 45%,48% 10%,65% 40%,82% 18%,100% 38%,100% 100%,0 100%)}"
 ".l2{height:260px;background:#e07a5f;clip-path:polygon(0 45%,20% 15%,38% 50%,55% 25%,75% 55%,90% 30%,100% 45%,100% 100%,0 100%)}"
 ".l3{height:190px;background:#81b29a;clip-path:polygon(0 30%,25% 60%,45% 20%,62% 55%,80% 25%,100% 50%,100% 100%,0 100%)}"
 ".l4{height:110px;background:#3d405b;clip-path:polygon(0 40%,18% 70%,40% 30%,60% 65%,85% 35%,100% 55%,100% 100%,0 100%)}"
 ".t{position:absolute;left:70px;top:70px;font:700 64px/1 Playfair;color:#3d405b}")

S["neon"] = lambda: page("""<div class=sky></div><div class=sun></div><div class=grid></div><div class=t>NIGHT DRIVE</div>""",
 "body{background:#12002b}.sky{position:absolute;inset:0;background:linear-gradient(#12002b 0%,#3a0a5c 50%,#ff2e88 64%,#12002b 64.2%)}"
 ".sun{position:absolute;left:330px;top:90px;width:300px;height:300px;border-radius:50%;background:linear-gradient(#ffe259,#ff4e9a 70%);"
 "-webkit-mask:linear-gradient(#000 55%,transparent 55% 60%,#000 60% 68%,transparent 68% 72%,#000 72% 79%,transparent 79% 83%,#000 83%);clip-path:inset(0 0 40% 0)}"
 ".grid{position:absolute;left:-200px;right:-200px;top:346px;height:340px;background:repeating-linear-gradient(90deg,#ff2e88 0 2px,transparent 2px 70px),"
 "repeating-linear-gradient(0deg,#ff2e88 0 2px,transparent 2px 40px);transform:perspective(260px) rotateX(62deg);transform-origin:top;opacity:.9}"
 ".t{position:absolute;left:0;right:0;top:330px;text-align:center;font:58px Orbitron;color:#fff;letter-spacing:.12em;text-shadow:0 0 8px #00f0ff,0 0 22px #00f0ff,0 0 44px #00f0ff}")

S["swiss"] = lambda: page("""<div class=n>26</div><div class=r></div><div class=t>Design<br>Week<br>Baghdad</div>
<div class=m>NOV 20—24<br>AL-MUTANABBI ST.<br>FREE ENTRY</div>""",
 "body{background:#f2efe9}.n{position:absolute;left:30px;top:-40px;font:400 470px/1 Anton;color:#e62020;letter-spacing:-.04em}"
 ".r{position:absolute;left:560px;top:0;width:16px;height:540px;background:#111}"
 ".t{position:absolute;left:610px;top:56px;font:700 58px/1 Grotesk;color:#111;letter-spacing:-.03em}"
 ".m{position:absolute;left:612px;bottom:56px;font:700 15px/1.6 Grotesk;color:#111;letter-spacing:.08em}")

S["doodle"] = lambda: page("""<svg width=960 height=540><rect width=960 height=540 fill="#fbfbf6"/>
<g fill=none stroke="#1f2937" stroke-width=4 stroke-linecap=round stroke-linejoin=round>
<path d="M120 300 q20 -90 110 -95 q95 -5 105 90 q5 85 -100 92 q-110 5 -115 -87z"/><path d="M190 280 l20 0 M265 280 l20 0 M205 330 q30 25 65 0"/>
<path d="M410 300 q60 -40 130 -10" stroke-dasharray="2 14"/><path d="M528 280 l20 18 l-26 10"/>
<rect x=600 y=190 width=240 height=170 rx=14 transform="rotate(-3 720 275)"/><path d="M630 240 h150 M630 280 h110 M630 320 h160"/>
<path d="M170 140 q30 -40 70 -10" stroke="#ef4444"/></g>
<text x=600 y=430 font-family=Caveat font-size=46 fill="#2563eb">idea → plan → done!</text>
<text x=120 y=110 font-family=Marker font-size=40 fill="#1f2937">Let me explain…</text></svg>""")

S["gradient"] = lambda: page("""<div class="b b1"></div><div class="b b2"></div><div class="b b3"></div>
<div class=g><small>NEW</small><b>Aurora</b><span>the collection is live</span><div class=btn>Explore →</div></div>""",
 "body{background:#0b0b1e;overflow:hidden}.b{position:absolute;border-radius:50%;filter:blur(60px)}"
 ".b1{left:-80px;top:-60px;width:520px;height:520px;background:#7c3aed}.b2{right:-60px;top:80px;width:480px;height:480px;background:#06b6d4}"
 ".b3{left:300px;bottom:-200px;width:420px;height:420px;background:#f472b6}"
 ".g{position:absolute;left:300px;top:120px;width:360px;height:300px;border-radius:24px;background:#ffffff1f;border:1px solid #ffffff55;backdrop-filter:blur(18px);"
 "padding:34px;color:#fff;box-shadow:0 20px 60px #0006}.g small{letter-spacing:.3em;opacity:.8}.g b{display:block;font:700 64px Grotesk;margin:8px 0 2px}"
 ".g span{opacity:.85}.btn{margin-top:38px;display:inline-block;background:#fff;color:#111;font:700 15px 'Segoe UI';padding:10px 18px;border-radius:99px}")

def peeps():
    P = lambda n: (DA / "Illustrations" / "Open Peeps" / "Standing" / f"peep-{n}.png").as_uri()
    cast = [(26, "#ffb4a2", 70), (46, "#a8dadc", 360), (52, "#ffd166", 650)]
    figs = "".join(f'<div class=c style="left:{x}px;background:{col}"></div><img class=p style="left:{x - 10}px" src="{P(n)}">' for n, col, x in cast)
    return page(f"""<div class=t>Meet your<br><b>care team</b></div><div class=hand>— no jargon, promise!</div>{figs}
<div class=bub>We'll walk you<br>through every step!</div><div class=ground></div>
<svg class=dood width=960 height=540><g fill=none stroke="#1d1d1b" stroke-width=3 stroke-linecap=round>
<path d="M610 70 l8 18 l18 8 l-18 8 l-8 18 l-8 -18 l-18 -8 l18 -8z"/><path d="M880 150 q14 -20 30 0"/><path d="M40 470 q20 -14 40 0 q20 14 40 0"/></g></svg>""",
                "body{background:#fff4e6}.t{position:absolute;left:70px;top:50px;font:400 40px/1.05 Grotesk;color:#1d1d1b}.t b{font-weight:700;font-size:56px}"
                ".hand{position:absolute;left:74px;top:178px;font:30px Caveat;color:#e76f51;transform:rotate(-3deg)}"
                ".c{position:absolute;bottom:58px;width:240px;height:240px;border-radius:50%}"
                ".p{position:absolute;bottom:58px;height:300px;width:260px;object-fit:contain;object-position:bottom}"
                ".ground{position:absolute;left:40px;right:40px;bottom:56px;height:4px;background:#1d1d1b;border-radius:4px}"
                ".bub{position:absolute;left:560px;top:120px;background:#fff;border:3px solid #1d1d1b;border-radius:22px;padding:14px 20px;"
                "font:600 22px/1.25 Grotesk;color:#1d1d1b;box-shadow:6px 6px 0 #1d1d1b}"
                ".bub:after{content:'';position:absolute;left:-26px;bottom:22px;border:14px solid transparent;border-right:16px solid #1d1d1b}"
                ".dood{position:absolute;inset:0;pointer-events:none}")
S["peeps"] = peeps

# ------------------------------------------------------------------ build + photograph
prof = HERE / ".chrome-profile"
done = []
for sid, fn in S.items():
    if ONLY and sid not in ONLY: continue
    html = WORK / f"{sid}.html"; html.write_text(fn(), encoding="utf-8")
    out = OUT / f"{sid}.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--user-data-dir={prof}", "--allow-file-access-from-files", "--virtual-time-budget=3000",
                    "--window-size=960,540", f"--screenshot={out}", html.as_uri()],
                   capture_output=True, creationflags=NOWIN, timeout=120)
    print(("OK " if out.exists() else "FAILED ") + sid, flush=True); done.append(sid)
