// Review Room front end: library, player with a frame-accurate timeline, pins/boxes on the frame, notes sent to Claude.
const $ = (s) => document.querySelector(s);
const api = (u, opt) => fetch(u, opt).then((r) => r.json());
const post = (u, body) => api(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
const enc = encodeURIComponent;

const S = { drops: [], videos: [], path: null, info: null, pin: null, box: null, rin: null, rout: null, zoom: 1,
  notes: [], sprite: null, compare: null, showingB: false, logFor: null, running: null };
const video = $("#video");

// ---------------------------------------------------------------- library
async function loadVideos() {
  S.videos = await api("/api/videos");
  renderLibrary();
  if (!S.videos.length) $("#videoList").innerHTML = '<div class="empty">No videos yet.<br>Drop video files here, or put them in the <b>workspace\\videos</b> folder.</div>';
}
function renderLibrary() {
  const q = $("#search").value.trim().toLowerCase();
  const list = $("#videoList"); list.innerHTML = "";
  let last = "";
  for (const v of S.videos) {
    if (q && !(v.name + " " + v.path).toLowerCase().includes(q)) continue;
    const head = v.kind === "final" ? `Videos · ${v.group}` : `Made by Claude · ${v.group}`;
    if (head !== last) { const g = document.createElement("div"); g.className = "group"; g.textContent = head; list.appendChild(g); last = head; }
    const el = document.createElement("div");
    el.className = "vid" + (v.path === S.path ? " active" : "");
    const rev = /\(rev \d+\)/.test(v.name) ? '<span class="badge">new version</span>' : "";
    el.innerHTML = `<img loading="lazy" src="/api/poster?path=${enc(v.path)}" alt=""><div><div class="t"></div>
      <div class="s">${(v.size / 1e6).toFixed(1)} MB ${rev}</div></div>`;
    el.querySelector(".t").textContent = v.name;
    el.title = v.path;
    const item = { kind: "video", path: v.path, name: v.name };
    el.dataset.key = keyOf(item); if (SEL.has(el.dataset.key)) el.classList.add("sel");
    const ck = document.createElement("span"); ck.className = "ck"; ck.title = "Select for Make a video (or Ctrl+click)";
    ck.onclick = (e) => { e.stopPropagation(); toggleSel(item); }; el.appendChild(ck);
    el.onclick = (e) => (e.ctrlKey || e.shiftKey || e.metaKey ? toggleSel(item) : openVideo(v.path));
    el.onmouseenter = () => qvShow(item, el); el.onmouseleave = qvHide;
    el.draggable = true;                                           // drag a video into the bin, onto the picture or into Make
    el.addEventListener("dragstart", (e) => { qvHide(); e.dataTransfer.setData("text/rr-asset", JSON.stringify({ kind: "footage", path: v.path, name: v.name })); });
    list.appendChild(el);
  }
}
$("#search").oninput = renderLibrary;

// ---------------------------------------------------------------- player
async function openVideo(path, keepTime) {
  const t = keepTime ? video.currentTime : 0;
  S.path = path; S.compare = null; S.showingB = false; $("#abBadge").classList.add("hidden");
  S.info = await api(`/api/info?path=${enc(path)}`);
  video.src = `/media?path=${enc(path)}`;
  video.currentTime = t;
  $("#stage").classList.add("on"); $("#empty").classList.add("hidden");
  S.drops = []; listDrops(); clearSpot(); S.rin = S.rout = null;
  S.sprite = null; S.zoom = 1; TL.thumbs = new Map(); TL.want = []; TL.peaks = null; syncZoomUi();
  const img = new Image(); img.onload = () => { if (S.path === path) { S.sprite = img; requestDraw(); } }; img.src = `/api/strip?path=${enc(path)}`;
  api(`/api/peaks?path=${enc(path)}`).then((j) => { if (S.path === path) { TL.peaks = j; requestDraw(); } });
  TL.cuts = []; TL.words = null; TL.wordsMsg = ""; hidePeek(); $("#colorModal").classList.add("hidden");
  api(`/api/cuts?path=${enc(path)}`).then((c) => { if (S.path === path && Array.isArray(c)) { TL.cuts = c; requestDraw(); } });
  loadTranscript(path, false);
  renderLibrary();
  await loadNotes();
  layout();
}
video.addEventListener("loadedmetadata", layout);
window.addEventListener("resize", layout);
new ResizeObserver(() => layout()).observe($("#stageWrap"));             // re-fit whenever the picture area changes size

function layout() {
  if (!S.info) return;
  const wrap = $("#stageWrap"), W = wrap.clientWidth - 24, H = wrap.clientHeight - 24;
  const ar = (S.info.width || 16) / (S.info.height || 9);
  let w = W, h = W / ar; if (h > H) { h = H; w = H * ar; }
  video.style.width = w + "px"; video.style.height = h + "px";
  drawTimeline(); drawOverlay();
}

const fps = () => (S.info && S.info.fps) || 30;
const dur = () => (S.info && S.info.duration) || video.duration || 1;
const frameOf = (t) => Math.floor(t * fps() + 1e-6);          // the frame on screen at time t
function tc(t) {
  const f = frameOf(t), F = Math.round(fps()), s = Math.floor(f / F), ff = f % F;
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}:${String(ff).padStart(2, "0")}`;
}
function seek(t) {
  t = Math.max(0, Math.min(dur() - 0.001, t)); video.currentTime = t;
  const x = (t / dur()) * tlW();                                   // keep the playhead on screen when zoomed in
  if (!dragging && (x < sc.scrollLeft || x > sc.scrollLeft + vw())) sc.scrollLeft = x - vw() / 2;
}
const snap = (t) => frameOf(t) / fps() + 0.0005;                 // the start of the frame under t
function stepFrames(n) { video.pause(); seek((frameOf(video.currentTime) + n) / fps() + 0.0005); }

$("#playBtn").onclick = () => (video.paused ? video.play() : video.pause());
$("#prevFrame").onclick = () => stepFrames(-1);
$("#nextFrame").onclick = () => stepFrames(1);
$("#vol").oninput = (e) => (video.volume = +e.target.value);
video.volume = 0.8;
video.addEventListener("play", () => ($("#playBtn").textContent = "❚❚"));
video.addEventListener("pause", () => ($("#playBtn").textContent = "▶"));
video.addEventListener("seeked", tick);
video.addEventListener("timeupdate", tick);
(function loop() { if (!video.paused) tick(); requestAnimationFrame(loop); })();

function tick() {
  const t = video.currentTime;
  $("#tc").textContent = tc(t);
  $("#frameNo").textContent = `frame ${frameOf(t)} · ${fps()} fps`;
  $("#cTime").textContent = tc(t);
  const W = tlW(), pxs = W / dur(), fpx = pxs / fps();
  const x = t * pxs;
  $("#playhead").style.left = x + "px";
  const band = $("#frameBand");                                    // the current frame, once frames are wide enough to see
  if (fpx >= 5) { band.style.left = (frameOf(t) / fps()) * pxs + "px"; band.style.width = fpx + "px"; band.classList.remove("hidden"); }
  else band.classList.add("hidden");
  if (!video.paused) {
    if (x < sc.scrollLeft + 40 || x > sc.scrollLeft + vw() - 40) sc.scrollLeft = x - vw() / 2;
  } else if (dragging) {
    if (x < sc.scrollLeft + 20) sc.scrollLeft = x - 20; else if (x > sc.scrollLeft + vw() - 20) sc.scrollLeft = x - vw() + 20;
  }
  drawOverlay();
}

// ---------------------------------------------------------------- timeline (zoomable; drawn only where it is visible)
const TL = { thumbs: new Map(), want: [], active: 0, peaks: null, visible: new Set(), cuts: [], words: null, wordsMsg: "" };
const sc = $("#tlScroll"), inner = $("#tlInner");
const vw = () => sc.clientWidth || 800;
const tlW = () => Math.max(vw(), Math.round(vw() * S.zoom));
const maxZoom = () => Math.max(2, (dur() * fps() * 60) / vw());   // all the way in: one frame is about 60 px wide

function setZoom(z, anchor) {                                      // anchor = x inside the visible timeline that stays put
  if (!S.info) return;
  z = Math.max(1, Math.min(maxZoom(), z));
  let tA;
  if (anchor == null) {                                            // buttons / keys zoom around the playhead (and bring it on screen)
    tA = video.currentTime; const px = (tA / dur()) * tlW() - sc.scrollLeft;
    anchor = px >= 0 && px <= vw() ? px : vw() / 2;
  } else tA = ((sc.scrollLeft + anchor) / tlW()) * dur();
  S.zoom = z; inner.style.width = tlW() + "px";
  sc.scrollLeft = (tA / dur()) * tlW() - anchor;
  syncZoomUi(); drawTimeline(); tick();
}
function syncZoomUi() {
  const mz = S.info ? maxZoom() : 2;
  $("#zoom").value = Math.round((Math.log(S.zoom) / Math.log(mz)) * 1000);
  if (!S.info || S.zoom <= 1.001) { $("#zoomInfo").textContent = "whole video"; return; }
  const pxs = tlW() / dur(), fpx = pxs / fps(), span = vw() / pxs;
  $("#zoomInfo").textContent = fpx >= 4 ? `1 frame = ${Math.round(fpx)} px` : span >= 1 ? `${span.toFixed(1)} s on screen` : `${Math.round(span * fps())} frames`;
}
$("#zoom").oninput = (e) => setZoom(Math.pow(maxZoom(), +e.target.value / 1000));
$("#zoomIn").onclick = () => setZoom(S.zoom * 1.6);
$("#zoomOut").onclick = () => setZoom(S.zoom / 1.6);
$("#zoomFit").onclick = () => setZoom(1);
sc.addEventListener("wheel", (e) => {                             // wheel = zoom at the mouse; Shift+wheel or sideways = pan
  if (!S.info) return;
  e.preventDefault();
  if (e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) { sc.scrollLeft += e.deltaX || e.deltaY; return; }
  setZoom(S.zoom * Math.exp(-e.deltaY * 0.0022), e.clientX - sc.getBoundingClientRect().left);
}, { passive: false });
let jog = 0;                                                       // wheel over the picture = step frame by frame
$("#stageWrap").addEventListener("wheel", (e) => {
  if (!S.info || (e.target.closest && e.target.closest(".drop"))) return;
  e.preventDefault(); jog += e.deltaY;
  if (Math.abs(jog) >= 40) { stepFrames(jog > 0 ? 1 : -1); jog = 0; }
}, { passive: false });

let drawQueued = false;
function requestDraw() { if (!drawQueued) { drawQueued = true; requestAnimationFrame(() => { drawQueued = false; drawTimeline(); }); } }
sc.addEventListener("scroll", requestDraw);

function drawTimeline() {
  if (!S.info) return;
  const W = tlW(); inner.style.width = W + "px";
  const x0 = sc.scrollLeft, w = vw(), d = dur(), F = fps(), pxs = W / d, fpx = pxs / F;
  const view = $("#tlView"); view.style.left = x0 + "px"; view.style.width = w + "px";
  const dpr = window.devicePixelRatio || 1;
  const prep = (cv, h) => {                                        // a canvas the size of the view, drawn in timeline coordinates
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); cv.style.width = w + "px"; cv.style.height = h + "px";
    const g = cv.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, -x0 * dpr, 0); return g;
  };
  // ruler
  const c = prep($("#ruler"), 22);
  c.font = "10px Consolas"; c.fillStyle = "#8b919c"; c.strokeStyle = "#3a3f4a";
  const ln = (x, y0, y1) => { c.beginPath(); c.moveTo(x, y0); c.lineTo(x, y1); c.stroke(); };
  if (fpx >= 6) for (let f = Math.floor(x0 / fpx); f * fpx <= x0 + w; f++) ln(Math.round(f * fpx) + 0.5, 17, 22);
  const steps = [1, 2, 5, 10, 15].map((k) => k / F).concat([0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300]).sort((a, b) => a - b);
  const step = steps.find((s) => s * pxs >= 70) || 300;
  for (let k = Math.floor(x0 / pxs / step); k * step * pxs <= x0 + w && k * step <= d + 1e-6; k++) {
    const t = k * step, x = Math.round(t * pxs) + 0.5;
    ln(x, 11, 22);
    c.fillText(step < 1 ? tc(t + 0.0005) : `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`, x + 3, 10);
    if (fpx < 6 && (step * pxs) / 5 >= 8) for (let j = 1; j < 5; j++) ln(Math.round((t + (step * j) / 5) * pxs) + 0.5, 18, 22);
  }
  // thumbnails: the 60-frame sprite when zoomed out, exact frames (fetched as needed) when zoomed in
  const g = prep($("#strip"), 64);
  g.fillStyle = "#000"; g.fillRect(x0, 0, w, 64);
  const ar = S.info.width && S.info.height ? S.info.width / S.info.height : 16 / 9;
  const base = Math.max(20, 64 * ar), perFrame = fpx >= base, slot = perFrame ? fpx : base;
  const exact = slot / pxs < d / 60;
  const need = [];
  for (let k = Math.floor(x0 / slot); k * slot < x0 + w; k++) {
    const x = k * slot, f = Math.max(0, Math.min(Math.floor(d * F) - 1, frameOf(x / pxs + 1e-4)));
    let src = null, sx = 0, sw = 0, sh = 0;
    if (exact) {
      const im = TL.thumbs.get(f);
      if (im && im.naturalWidth) { src = im; sw = im.naturalWidth; sh = im.naturalHeight; } else if (!im) need.push(f);
    }
    if (!src && S.sprite) {
      const n = 60, i = Math.min(n - 1, Math.max(0, Math.floor((f / F / d) * n)));
      src = S.sprite; sw = S.sprite.width / n; sx = i * sw; sh = S.sprite.height;
    }
    const dw = Math.min(slot - 1, 64 * ar), dx = x + (slot - 1 - dw) / 2;
    if (src) g.drawImage(src, sx, 0, sw, sh, dx, 0, dw, 64);
    if (perFrame) { g.fillStyle = "#000"; g.fillRect(x + slot - 1, 0, 1, 64); }
  }
  const mid = ((x0 + w / 2) / pxs) * F;
  TL.want = need.sort((a, b) => Math.abs(a - mid) - Math.abs(b - mid)); TL.visible = new Set(need);
  pumpThumbs();
  // waveform from audio peaks (sharp at every zoom)
  const wv = prep($("#wave"), 54);
  wv.fillStyle = "#0e1a16"; wv.fillRect(x0, 0, w, 54);
  if (TL.peaks && TL.peaks.p && TL.peaks.p.length) {
    const P = TL.peaks.p, rate = TL.peaks.rate; wv.fillStyle = "#5fd3a8";
    for (let x = Math.floor(x0); x < x0 + w; x++) {
      const a = Math.floor((x / pxs) * rate), b = Math.max(a + 1, Math.floor(((x + 1) / pxs) * rate));
      if (a >= P.length) break;
      let m = 0; for (let i = a; i < b && i < P.length; i++) if (P[i] > m) m = P[i];
      const hh = Math.max(0.5, Math.sqrt(m / 255) * 25); wv.fillRect(x, 27 - hh, 1, hh * 2);
    }
  } else if (TL.peaks) { wv.fillStyle = "#4d5a55"; wv.font = "11px Segoe UI"; wv.fillText("no audio", x0 + 8, 31); }
  // shot cuts: cyan lines on the thumbnails, little triangles on the ruler
  for (const ct of TL.cuts) {
    const x = Math.round(ct * pxs) + 0.5;
    if (x < x0 - 5 || x > x0 + w + 5) continue;
    g.fillStyle = "#3fd0ff"; g.fillRect(x - 1, 0, 2, 64);
    c.fillStyle = "#3fd0ff"; c.beginPath(); c.moveTo(x - 4, 22); c.lineTo(x + 4, 22); c.lineTo(x, 15); c.fill();
  }
  // spoken words lane
  const wd = prep($("#words"), 20);
  wd.fillStyle = "#15171b"; wd.fillRect(x0, 0, w, 20);
  if (TL.words && TL.words.length) {
    wd.font = "12px 'Segoe UI', 'Noto Sans Arabic', Tahoma"; wd.textBaseline = "middle";
    TL.words.forEach((wo, i) => {
      const a = wo.start * pxs, b = Math.max(a + 3, wo.end * pxs);
      if (b < x0 || a > x0 + w) return;
      wd.fillStyle = i % 2 ? "#28324a" : "#34415f"; wd.fillRect(a, 2, Math.max(2, b - a - 1), 16);
      const tw = wd.measureText(wo.text).width;
      if (tw + 4 <= b - a) { wd.fillStyle = "#e6e8ec"; wd.fillText(wo.text, a + (b - a - tw) / 2, 10.5); }
    });
  } else if (TL.wordsMsg) { wd.fillStyle = "#5d6570"; wd.font = "11px 'Segoe UI'"; wd.textBaseline = "middle"; wd.fillText(TL.wordsMsg, x0 + 8, 10.5); }
  drawRange(); drawMarkers(); syncZoomUi();
}

function pumpThumbs() {
  while (TL.active < 4 && TL.want.length) {
    const f = TL.want.shift();
    if (TL.thumbs.has(f) || !TL.visible.has(f)) continue;
    const im = new Image(), path = S.path;
    TL.thumbs.set(f, im); TL.active++;
    im.onload = im.onerror = () => { TL.active--; if (path === S.path) requestDraw(); pumpThumbs(); };
    im.src = `/api/thumb?path=${enc(path)}&f=${f}`;
  }
  if (TL.thumbs.size > 3000) for (const k of [...TL.thumbs.keys()].slice(0, 1000)) TL.thumbs.delete(k);
}

let dragging = false;
const cutTime = (ct) => Math.round(ct * fps()) / fps() + 0.0005;   // first frame of the new shot
function rawTime(e) { const r = inner.getBoundingClientRect(); return ((e.clientX - r.left) / r.width) * dur(); }
function tlTime(e) {                                               // whole frames; snaps to a cut within 7 px
  const r = inner.getBoundingClientRect(), t = rawTime(e), pxs = r.width / dur();
  for (const ct of TL.cuts) if (Math.abs(ct - t) * pxs < 7) return cutTime(ct);
  return snap(t);
}
const inLane = (e) => e.clientY - inner.getBoundingClientRect().top >= 147;
const wordAt = (e) => TL.words && TL.words.find((w) => { const t = rawTime(e); return t >= w.start - 0.02 && t <= w.end + 0.02; });
inner.addEventListener("mousedown", (e) => {
  if (e.target.classList.contains("mk") || !S.info) return;
  const wo = inLane(e) && wordAt(e);
  if (wo) {                                                        // click a word = jump to it; Shift+click = add it to the range
    video.pause();
    if (e.shiftKey) {
      remember("range from words");
      if (S.rin == null) { S.rin = wo.start; S.rout = wo.end; }
      else { const a = Math.min(S.rin, S.rout, wo.start), b = Math.max(S.rin, S.rout, wo.end); S.rin = a; S.rout = b; }
      drawRange();
    }
    seek(snap(wo.start + 0.001)); return;
  }
  dragging = true; video.pause(); seek(tlTime(e));
});
window.addEventListener("mousemove", (e) => { if (dragging) seek(tlTime(e)); });
window.addEventListener("mouseup", () => (dragging = false));
inner.addEventListener("mousemove", (e) => {                       // hover: the exact time and frame under the mouse
  if (!S.info) return;
  const t = tlTime(e), x = (t / dur()) * tlW(), sx = x - sc.scrollLeft;
  const hl = $("#hoverLine"), tip = $("#hoverTip");
  hl.style.left = x + "px"; hl.classList.remove("hidden");
  const wo = inLane(e) && wordAt(e);
  tip.textContent = wo ? `«${wo.text}» ${tc(wo.start)}  (click = jump, Shift+click = add to range)` : `${tc(t)} · frame ${frameOf(t)}`; tip.style.left = Math.max(60, Math.min(vw() - 60, sx)) + "px"; tip.classList.remove("hidden");
});
inner.addEventListener("mouseleave", () => { $("#hoverLine").classList.add("hidden"); $("#hoverTip").classList.add("hidden"); });

function drawRange() {
  const el = $("#range");
  if (S.rin == null || S.rout == null || !S.info) { el.classList.add("hidden"); $("#cRange").classList.add("hidden"); return; }
  const W = tlW(), a = Math.min(S.rin, S.rout), b = Math.max(S.rin, S.rout);
  el.style.left = (a / dur()) * W + "px"; el.style.width = ((b - a) / dur()) * W + "px"; el.classList.remove("hidden");
  $("#cRange").textContent = `range ${tc(a)} → ${tc(b)}`; $("#cRange").classList.remove("hidden");
}
$("#inBtn").onclick = () => { remember("range in"); S.rin = video.currentTime; if (S.rout == null) S.rout = Math.min(dur(), S.rin + 1); drawRange(); };
$("#outBtn").onclick = () => { remember("range out"); S.rout = video.currentTime; if (S.rin == null) S.rin = Math.max(0, S.rout - 1); drawRange(); };
$("#clearRange").onclick = () => { remember("clear the range"); S.rin = S.rout = null; drawRange(); };

function drawMarkers() {
  const box = $("#markers"); box.innerHTML = "";
  if (!S.info) return;
  const W = tlW();
  S.drops.forEach((d) => {                                        // assets dropped for the note being written
    if (d.t == null) return;
    const m = document.createElement("div"); m.className = "dmk"; m.style.left = (d.t / dur()) * W + "px"; box.appendChild(m);
  });
  S.notes.forEach((n, i) => {
    const m = document.createElement("div");
    m.className = "mk" + (n.status === "review" ? " review" : n.by === "claude" ? " ai" : "");
    m.dataset.n = i + 1; m.style.left = (n.t / dur()) * W + "px"; m.title = n.text;
    m.onclick = () => { video.pause(); seek(n.t); };
    box.appendChild(m);
  });
}

// ---------------------------------------------------------------- pins / boxes on the frame
let down = null;
const ov = $("#overlay");
function rel(e) { const r = ov.getBoundingClientRect(); return [Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), Math.min(1, Math.max(0, (e.clientY - r.top) / r.height))]; }
ov.addEventListener("mousedown", (e) => { if (e.button !== 0) return; remember("pin / box"); S.selDrop = null; video.pause(); down = rel(e); });
window.addEventListener("mousemove", (e) => {                     // a box can be drawn in any direction, even past the picture's edge
  if (!down) return;
  const p = rel(e);
  S.box = [Math.min(down[0], p[0]), Math.min(down[1], p[1]), Math.max(down[0], p[0]), Math.max(down[1], p[1])]; S.pin = null; drawOverlay();
});
window.addEventListener("mouseup", (e) => {
  if (!down) return;
  const p = rel(e), r = ov.getBoundingClientRect();
  if (Math.hypot((p[0] - down[0]) * r.width, (p[1] - down[1]) * r.height) < 6) { S.pin = p; S.box = null; }
  else { S.box = [Math.min(down[0], p[0]), Math.min(down[1], p[1]), Math.max(down[0], p[0]), Math.max(down[1], p[1])]; S.pin = null; }
  down = null; drawOverlay(); updateSpot(); $("#noteText").focus();
});
function clearSpot() { S.pin = null; S.box = null; drawOverlay(); updateSpot(); }
function updateSpot() {
  const el = $("#cSpot");
  if (S.pin) { el.textContent = `pin ${Math.round(S.pin[0] * 100)}%, ${Math.round(S.pin[1] * 100)}%`; el.classList.remove("muted"); }
  else if (S.box) { el.textContent = `box ${Math.round(S.box[0] * 100)},${Math.round(S.box[1] * 100)} → ${Math.round(S.box[2] * 100)},${Math.round(S.box[3] * 100)}%`; el.classList.remove("muted"); }
  else { el.textContent = "no spot (click the video)"; el.classList.add("muted"); }
}
function drawOverlay() {
  ov.innerHTML = "";
  const t = video.currentTime, near = 0.35;
  S.notes.forEach((n, i) => {
    if (Math.abs(n.t - t) > near) return;
    if (n.box) addBox(n.box, "old"); else if (n.x != null) addPin([n.x, n.y], "old", i + 1);
  });
  if (S.box) addBox(S.box, ""); if (S.pin) addPin(S.pin, "", "");
  addDrops();
}
function addPin(p, cls, label) {
  const d = document.createElement("div"); d.className = "pin " + cls;
  d.style.left = p[0] * 100 + "%"; d.style.top = p[1] * 100 + "%";
  if (label !== "") d.innerHTML = `<span>${label}</span>`;
  ov.appendChild(d);
}
function addBox(b, cls) {
  const d = document.createElement("div"); d.className = "box " + cls;
  d.style.left = b[0] * 100 + "%"; d.style.top = b[1] * 100 + "%";
  d.style.width = (b[2] - b[0]) * 100 + "%"; d.style.height = (b[3] - b[1]) * 100 + "%";
  ov.appendChild(d);
}

// the exact frame at full resolution with the pin/box burned in, for Claude to look at
function captureFrame() {
  const w = video.videoWidth, h = video.videoHeight, cv = document.createElement("canvas");
  cv.width = w; cv.height = h; const g = cv.getContext("2d");
  g.drawImage(video, 0, 0, w, h);
  const lw = Math.max(4, Math.round(w / 220));
  g.lineWidth = lw; g.strokeStyle = "#ff2d43";
  if (S.pin) {
    const x = S.pin[0] * w, y = S.pin[1] * h, R = Math.max(18, w / 40);
    g.strokeStyle = "#fff"; g.lineWidth = lw + 4; g.beginPath(); g.arc(x, y, R, 0, 7); g.stroke();
    g.strokeStyle = "#ff2d43"; g.lineWidth = lw; g.beginPath(); g.arc(x, y, R, 0, 7); g.stroke();
    g.fillStyle = "#ff2d43"; g.beginPath(); g.arc(x, y, lw, 0, 7); g.fill();
  } else if (S.box) {
    const [a, b, c2, d] = S.box;
    g.strokeStyle = "#fff"; g.lineWidth = lw + 4; g.strokeRect(a * w, b * h, (c2 - a) * w, (d - b) * h);
    g.strokeStyle = "#ff2d43"; g.lineWidth = lw; g.strokeRect(a * w, b * h, (c2 - a) * w, (d - b) * h);
  }
  burnDrops(g, w, h, lw);
  return cv.toDataURL("image/png");
}

// ---------------------------------------------------------------- notes
async function saveNote(send) {
  const text = $("#noteText").value.trim();
  if (!S.path) return alert("Pick a video first.");
  if (!text) { $("#noteText").focus(); return; }
  video.pause();
  const t = video.currentTime;
  const png = captureFrame();
  const body = { video: S.path, t, text, png, send, level: $("#levelSel").value, style: STYLE.editor, engine: ENGINE, assets: S.drops.map(({ thumb, ...a }) => a),
    x: S.pin ? S.pin[0] : null, y: S.pin ? S.pin[1] : null, box: S.box,
    rin: S.rin != null ? Math.min(S.rin, S.rout) : null, rout: S.rout != null ? Math.max(S.rin, S.rout) : null };
  const n = await post("/api/notes", body);
  $("#noteText").value = ""; S.drops = []; renderDrops(); clearSpot();
  await loadNotes();
  if (send) openLog(n.id);
}
$("#saveNote").onclick = () => saveNote(false);
$("#sendNote").onclick = () => saveNote(true);

async function loadNotes() {
  if (!S.path) return;
  const j = await api(`/api/notes?path=${enc(S.path)}`);
  S.notes = j.notes.sort((a, b) => a.t - b.t); S.running = j.running;
  const cs = $("#claudeState");
  if (!j.claude) { cs.textContent = "Claude CLI missing"; cs.className = "pill bad"; }
  else if (j.running) { cs.textContent = `Claude working${j.queued ? ` · ${j.queued} queued` : ""}`; cs.className = "pill busy"; }
  else { cs.textContent = "Claude ready"; cs.className = "pill ok"; }
  $("#queueInfo").textContent = S.notes.length ? `(${S.notes.length})` : "";
  const drafts = S.notes.filter((n) => n.status === "draft" && !n.kind).length;
  $("#sendAll").classList.toggle("hidden", drafts < 2); $("#sendAll").textContent = `Send all ${drafts} drafts ➜`;
  renderNotes(); drawMarkers(); drawOverlay();
}

const LABEL = { draft: "draft", queued: "queued", running: "Claude is working…", approving: "applying approval…",
  review: "new version ready", approved: "approved ✓", done: "done", failed: "failed", cancelled: "stopped" };

function renderNotes() {
  const box = $("#notes"); box.innerHTML = "";
  if (!S.notes.length) { box.innerHTML = '<div class="muted">No notes yet. Pause on a moment, click the spot, write the edit.</div>'; return; }
  S.notes.forEach((n, i) => {
    const el = document.createElement("div"); el.className = "note" + (n.by === "claude" ? " ai" : "");
    const KIND = { check: "🔍 AI check", color: "🎨 colour", look: "🎨 look" };
    const chips = (n.by === "claude" ? '<span class="chip ai">🤖 found by AI check</span>' : "")
      + (n.severity ? `<span class="chip sev-${n.severity}">${n.severity}</span>` : "")
      + (KIND[n.kind] ? `<span class="chip ai">${KIND[n.kind]}</span>` : "")
      + (n.engine === "codex" ? '<span class="chip eng">Codex</span>' : "")
      + (n.batch_ids && n.batch_ids.length > 1 ? `<span class="chip batch">batch of ${n.batch_ids.length}</span>` : "");
    el.innerHTML = `<div class="top"><span class="num">${i + 1}</span><span class="chip when">${tc(n.t)}</span>
      <span class="st ${n.status}">${LABEL[n.status] || n.status}</span><div class="spacer"></div></div>
      ${chips ? `<div class="meta">${chips}</div>` : ""}
      <img class="thumb" src="/api/frame?id=${n.id}" alt=""><div class="txt" dir="auto"></div>
      ${n.assets && n.assets.length ? '<div class="assets"></div>' : ""}
      ${n.summary ? '<div class="sum" dir="auto"></div>' : ""}<div class="acts"></div>`;
    if (n.assets && n.assets.length) el.querySelector(".assets").textContent = "📎 " + n.assets.map((a, k) => `${k + 1}. ${a.name || a.block}`).join("   ");
    el.querySelector(".txt").textContent = n.text;
    if (n.summary) el.querySelector(".sum").textContent = n.summary;
    el.querySelector(".when").onclick = () => { video.pause(); seek(n.t); };
    el.querySelector(".thumb").onclick = () => window.open(`/api/frame?id=${n.id}`, "_blank");
    el.querySelector(".thumb").onerror = (ev) => ev.target.remove();
    const acts = el.querySelector(".acts");
    const b = (label, fn, cls = "ghost") => { const x = document.createElement("button"); x.className = cls; x.textContent = label; x.onclick = fn; acts.appendChild(x); };
    const busy = ["queued", "running", "approving"].includes(n.status);
    if (busy || n.started) b("Progress", () => openLog(n.id));
    if (["draft", "failed", "cancelled", "done"].includes(n.status)) b(n.status === "draft" ? "Send to Claude ➜" : n.kind ? "Run again" : "Send again", () => post(`/api/notes/${n.id}/send`).then(() => { openLog(n.id); loadNotes(); }), n.status === "draft" ? "primary" : "ghost");
    if (n.status === "review" && n.result) {
      b(S.compare === n.result && S.showingB ? "Show original (A)" : "Compare A/B", () => toggleCompare(n.result));
      b("Open new version", () => openVideo(n.result, true));
      b("Approve ✓", () => { if (confirm("Approve the new version? The old one goes to the Recycle Bin and the new one takes its name.")) post(`/api/notes/${n.id}/approve`).then(() => { openLog(n.id); loadNotes(); }); }, "primary");
    }
    if (!busy) b("Delete", () => deleteNote(n));
    box.appendChild(el);
  });
}
setInterval(() => { if (document.hidden) return; if (S.path) loadNotes(); if (S.logFor) refreshLog(); }, 1500);

function toggleCompare(resultPath) {
  const t = video.currentTime, playing = !video.paused;
  if (S.compare !== resultPath) { S.compare = resultPath; S.showingB = false; }
  S.showingB = !S.showingB;
  video.src = `/media?path=${enc(S.showingB ? resultPath : S.path)}`;
  video.addEventListener("loadedmetadata", () => { video.currentTime = t; if (playing) video.play(); }, { once: true });
  $("#abBadge").classList.toggle("hidden", !S.showingB);
  renderNotes();
}

// ---------------------------------------------------------------- Claude progress drawer
function openLog(id) { S.logFor = id; $("#drawer").classList.remove("hidden"); $("#drawerTitle").textContent = "Progress · " + id; refreshLog(); }
$("#closeDrawer").onclick = () => { S.logFor = null; $("#drawer").classList.add("hidden"); };
$("#cancelJob").onclick = () => S.logFor && post(`/api/notes/${S.logFor}/cancel`).then(loadNotes);
async function refreshLog() {
  const lines = await api(`/api/log?id=${S.logFor}`);
  const box = $("#log"), atEnd = box.scrollTop + box.clientHeight >= box.scrollHeight - 30;
  box.innerHTML = "";
  if (!lines.length) box.innerHTML = '<div class="sys">Waiting for Claude to start…</div>';
  for (const [k, txt] of lines) { const d = document.createElement("div"); d.className = k; d.dir = "auto"; d.textContent = (k === "tool" ? "› " : "") + txt; box.appendChild(d); }
  if (atEnd) box.scrollTop = box.scrollHeight;
  $("#cancelJob").classList.toggle("hidden", S.running !== S.logFor);
}

// ---------------------------------------------------------------- keys + quit
window.addEventListener("keydown", (e) => {
  if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT" || e.target.tagName === "SELECT") {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && e.target.id === "noteText") saveNote(true);
    return;
  }
  if (e.code === "Space") { e.preventDefault(); video.paused ? video.play() : video.pause(); }
  else if (e.key === "ArrowLeft") { e.preventDefault(); e.shiftKey ? (video.pause(), seek(snap(video.currentTime - 1))) : stepFrames(-1); }
  else if (e.key === "ArrowRight") { e.preventDefault(); e.shiftKey ? (video.pause(), seek(snap(video.currentTime + 1))) : stepFrames(1); }
  else if (e.key === "ArrowUp") { e.preventDefault(); jumpCut(-1); }
  else if (e.key === "ArrowDown") { e.preventDefault(); jumpCut(1); }
  else if (e.key === "i" || e.key === "I") $("#inBtn").click();
  else if (e.key === "o" || e.key === "O") $("#outBtn").click();
  else if (e.key === "Escape") { if (S.pin || S.box) remember("clear the spot"); clearSpot(); }
  else if (e.key === "=" || e.key === "+") setZoom(S.zoom * 1.6);
  else if (e.key === "-" || e.key === "_") setZoom(S.zoom / 1.6);
  else if (e.key === "\\") setZoom(1);
  else if (e.key === "Home") seek(0);
  else if (e.key === "End") seek(dur());
});
$("#quitBtn").onclick = () => { if (confirm("Close the Review Room? Running Claude jobs will stop.")) post("/api/quit").then(() => window.close()); };

// ---------------------------------------------------------------- shot cuts (↑ / ↓)
function jumpCut(dir) {
  if (!S.info || !TL.cuts.length) return;
  const f = frameOf(video.currentTime), frames = TL.cuts.map((c) => Math.round(c * fps()));
  const next = dir > 0 ? frames.find((x) => x > f) : [...frames].reverse().find((x) => x < f);
  video.pause(); seek(next != null ? next / fps() + 0.0005 : dir > 0 ? dur() : 0);
}
$("#prevCut").onclick = () => jumpCut(-1);
$("#nextCut").onclick = () => jumpCut(1);

// ---------------------------------------------------------------- transcript lane
async function loadTranscript(path, start) {
  if (start) await post("/api/transcript", { path });
  const j = await api(`/api/transcript?path=${enc(path)}`);
  if (S.path !== path) return;
  const btn = $("#txBtn");
  if (j.status === "done") {
    TL.words = j.words; TL.wordsMsg = j.words.length ? "" : "no speech found in this video";
    btn.classList.add("on"); btn.textContent = "Transcript ✓";
  } else {
    TL.words = null; btn.classList.remove("on");
    if (j.status === "none") { TL.wordsMsg = "press Transcript (above) to show the spoken words here"; btn.textContent = "Transcript"; }
    else if (j.status.startsWith("failed")) { TL.wordsMsg = "transcript " + j.status; btn.textContent = "Transcript (retry)"; }
    else {
      TL.wordsMsg = j.status === "queued" ? "transcript queued: it starts when the running job finishes…" : "transcribing with whisper…";
      btn.textContent = "Transcript…"; setTimeout(() => loadTranscript(path, false), 2500);
    }
  }
  requestDraw();
}
$("#txBtn").onclick = () => S.path && loadTranscript(S.path, true);

// ---------------------------------------------------------------- phone safe zones
const SAFE = {                                                     // [x0, y0, x1, y1, label] as fractions of a 9:16 frame
  ig: [[0, 0, 1, 0.12, "top bar"], [0, 0.78, 1, 1, "caption · username · audio"], [0.86, 0.42, 1, 0.78, "like comment share"]],
  tt: [[0, 0, 1, 0.1, "Following · For You"], [0, 0.77, 1, 1, "caption · sound"], [0.85, 0.38, 1, 0.77, "profile like comment share"]],
  yt: [[0, 0, 1, 0.09, "top bar"], [0, 0.8, 1, 1, "title · channel"], [0.86, 0.45, 1, 0.8, "like comment share"]],
};
function drawSafe() {
  const k = $("#safeSel").value, box = $("#safe"); box.innerHTML = ""; box.classList.toggle("hidden", !k);
  if (!k) return;
  for (const [a, b, c, d, label] of SAFE[k]) {
    const z = document.createElement("div"); z.className = "z"; z.textContent = label;
    Object.assign(z.style, { left: a * 100 + "%", top: b * 100 + "%", width: (c - a) * 100 + "%", height: (d - b) * 100 + "%" });
    box.appendChild(z);
  }
}
$("#safeSel").onchange = () => { drawSafe(); $("#safeSel").blur(); };

// ---------------------------------------------------------------- one-click AI actions (fill the note; adjust; send)
const ACTIONS = [
  ["🐢 Slow motion", "RIFE frame interpolation on the range",
    "Make the marked range (or this shot) smooth slow motion at 50% speed using RIFE frame interpolation (video2x). Keep the music continuous and in sync, and never slow down a voice."],
  ["🔍 Upscale to 4K", "Real-ESRGAN, whole video",
    "Upscale this video to 4K (2160 px on the long side) with Real-ESRGAN (video2x). Keep everything else identical."],
  ["🫥 Blur / hide (box)", "follows the object if it moves",
    "Blur and hide what is inside the box for the marked range (or the whole shot). If it moves (a face, a plate, a logo), track it so the blur follows it."],
  ["✂️ Remove background (pin)", "Robust Video Matting cut-out",
    "Cut out the subject at the pin for this shot with Robust Video Matting and replace the background with: "],
  ["🎯 Stabilize", "ffmpeg vidstab, smallest crop",
    "Stabilize the shaky footage in the marked range (or this shot) with ffmpeg vidstab (two passes), using the smallest crop/zoom needed."],
  ["🔇 Remove silences", "cuts only inside measured silence",
    "Remove dead air and long pauses from the voice in the marked range (or the whole video). Cut only inside measured silence (ffmpeg silencedetect / word timings), never inside a word, keep pauses natural (about 0.25–0.35 s) and the music smooth across the cuts."],
  ["💬 Arabic captions", "word-timed, phone-safe",
    "Add Arabic captions in the spoken dialect (spell چ/گ as spoken), word-timed to the voice (whisper --language ar), in the house caption style, readable on a phone and outside the Instagram/TikTok UI zones."],
  ["🎧 Clean the voice", "noise, hum, clicks, -14 LUFS",
    "Clean the voice: remove background noise and hum, de-click, keep it natural, then normalise the mix to -14 LUFS with true peak at or below -1 dBTP."],
  ["🌫️ Reduce video noise", "denoise without smearing",
    "Reduce video noise/grain in the marked range (or this shot) without smearing detail (ffmpeg nlmeans or hqdn3d), keeping it sharp."],
];
(function buildActions() {
  const m = $("#actMenu");
  for (const [label, hint, text] of ACTIONS) {
    const d = document.createElement("div"); d.innerHTML = "<b></b><small></small>";
    d.querySelector("b").textContent = label; d.querySelector("small").textContent = hint;
    d.onclick = () => {
      const ta = $("#noteText"); ta.value = ta.value.trim() ? ta.value.trim() + "\n" + text : text;
      m.classList.add("hidden"); ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);
    };
    m.appendChild(d);
  }
})();
$("#actBtn").onclick = (e) => { e.stopPropagation(); $("#actMenu").classList.toggle("hidden"); };
document.addEventListener("click", (e) => { if (!e.target.closest(".dd")) $("#actMenu").classList.add("hidden"); });

// ---------------------------------------------------------------- send all drafts
$("#sendAll").onclick = async () => {
  const j = await post("/api/batch", { path: S.path, level: $("#levelSel").value, style: STYLE.editor, engine: ENGINE });
  if (j.error) return alert(j.error);
  openLog(j.lead); loadNotes();
};

// ---------------------------------------------------------------- colour: auto fix, match to a reference, LUT looks
const COL = { lut: null, ref: null };
try { COL.ref = JSON.parse(localStorage.getItem("rr.ref") || "null"); } catch (e) { COL.ref = null; }
const strength = () => +$("#colStrength").value / 100;
$("#colStrength").oninput = () => ($("#colStrengthV").textContent = $("#colStrength").value + "%");
$("#colorBtn").onclick = () => {
  if (!S.path) return alert("Pick a video first.");
  video.pause(); $("#colorModal").classList.remove("hidden"); refInfo(); buildLooks();
};
$("#colorClose").onclick = () => { $("#colorModal").classList.add("hidden"); hidePeek(); };
function refInfo() {
  const r = COL.ref;
  $("#refInfo").textContent = r ? `Reference: "${r.name}" at ${tc(r.t)}. To change it, pause on another frame and press the button again.`
    : 'Pause on a frame whose colours you like (in any video) and press "Use this frame".';
  $("#matchGo").disabled = !r;
}
$("#refSet").onclick = () => {
  COL.ref = { path: S.path, t: video.currentTime, name: S.path.split("/").pop().replace(/\.\w+$/, "") };
  try { localStorage.setItem("rr.ref", JSON.stringify(COL.ref)); } catch (e) { /* per-viewer convenience only */ }
  refInfo();
};
async function colorJob(url, body) {
  const n = await post(url, { path: S.path, t: video.currentTime, strength: strength(), ...body });
  if (n.error) return alert(n.error);
  $("#colorModal").classList.add("hidden"); hidePeek(); openLog(n.id); loadNotes();
}
$("#autoGo").onclick = () => colorJob("/api/color", { mode: "auto" });
$("#matchGo").onclick = () => COL.ref && colorJob("/api/color", { mode: "match", ref_path: COL.ref.path, ref_t: COL.ref.t });
$("#lookGo").onclick = () => COL.lut && colorJob("/api/look", { lut: COL.lut });
let LUTS = null;
async function buildLooks() {
  if (!LUTS) LUTS = await api("/api/luts");
  const grid = $("#lookGrid"), t = video.currentTime.toFixed(3); grid.innerHTML = "";
  for (const name of ["", ...LUTS]) {
    const d = document.createElement("div"); d.className = "lk" + ((COL.lut || "") === name ? " sel" : "");
    const src = (h) => `/api/lookpreview?path=${enc(S.path)}&t=${t}&lut=${enc(name)}&h=${h}`;
    d.innerHTML = "<img alt=\"\"><span></span>";
    d.querySelector("img").src = src(240); d.querySelector("span").textContent = name || "original";
    d.onclick = () => {
      grid.querySelectorAll(".lk").forEach((x) => x.classList.remove("sel")); d.classList.add("sel");
      COL.lut = name || null; $("#lookGo").disabled = !name;
      $("#lookGo").textContent = name ? `Apply look "${name}" at ${$("#colStrength").value}%` : "Apply look";
      if (name) peek(src(Math.min(1080, (S.info && S.info.height) || 1080)), `preview: ${name} (100%)`); else hidePeek();
    };
    grid.appendChild(d);
  }
}
function peek(src, label) { $("#lookPeek").src = src; $("#lookPeek").classList.remove("hidden"); $("#peekBadge").textContent = label; $("#peekBadge").classList.remove("hidden"); }
function hidePeek() { $("#lookPeek").classList.add("hidden"); $("#peekBadge").classList.add("hidden"); }
video.addEventListener("play", hidePeek);
video.addEventListener("seeked", () => { if (!$("#lookPeek").classList.contains("hidden")) hidePeek(); });

// ---------------------------------------------------------------- assets & effects: your bin, quick view, drag into the video, place
const KINDS = [["", "All"], ["brand", "Brands"], ["effect", "Effects"], ["emoji", "Emoji"], ["icon", "Icons"], ["image", "Images"],
  ["footage", "Footage"], ["music", "Music"], ["sfx", "SFX"], ["audio", "Audio"], ["lut", "Looks"], ["font", "Fonts"], ["3d", "3D"], ["file", "Other"]];
const VISUAL = new Set(["brand", "emoji", "icon", "image", "footage"]);
const AUDIO = new Set(["music", "sfx", "audio"]);
const ICON = { music: "🎵", sfx: "🔊", audio: "🎵", effect: "✨", lut: "🎨", font: "🔤", "3d": "🧊", lottie: "🎞️", file: "📄",
  brand: "🏷️", emoji: "😀", icon: "◆", image: "🖼️", footage: "🎬", video: "🎬" };
const keyOf = (a) => (a.kind === "video" ? "video:" + a.path : a.path || "hf:" + a.block);
let BIN = [], binKind = "", libKind = "", libTimer = null, fontN = 0;
const clamp01 = (v) => Math.max(0, Math.min(1, v));
const DIMG = {};                                                   // loaded images of placed assets (for the frame image)
const dimg = (src) => DIMG[src] || (DIMG[src] = Object.assign(new Image(), { src }));
const FONTS = {};
function fontFam(a) {
  if (!FONTS[a.path]) {
    FONTS[a.path] = "rrfont" + ++fontN;
    new FontFace(FONTS[a.path], `url(/api/asset?path=${enc(a.path)})`).load().then((f) => document.fonts.add(f)).catch(() => {});
  }
  return FONTS[a.path];
}
function thumbOf(a) {
  if (!a.path) return null;
  if (a.kind === "footage" || a.kind === "video") return `/api/poster?path=${enc(a.path)}`;
  if (VISUAL.has(a.kind)) return `/api/asset?path=${enc(a.path)}`;
  return null;
}

function showTab(assets) {
  $("#videosPane").classList.toggle("hidden", assets); $("#assetsPane").classList.toggle("hidden", !assets);
  $("#tabVideos").classList.toggle("on", !assets); $("#tabAssets").classList.toggle("on", assets);
  document.querySelector("main").classList.toggle("wideLib", assets); layout();
  if (assets) loadBin();
  else document.body.classList.remove("bigAssets");
}
$("#tabVideos").onclick = () => showTab(false);
$("#tabAssets").onclick = () => showTab(true);

// ---- your bin (starts with one item of each type)
async function loadBin() { BIN = await api("/api/bin"); renderBin(); }
function chips(box, current, kinds, pick) {
  box.innerHTML = "";
  for (const [k, label] of KINDS) {
    if (k && kinds && !kinds.has(k)) continue;
    const b = document.createElement("button"); b.className = "ghost" + (k === current ? " on" : ""); b.textContent = label;
    b.onclick = () => pick(k); box.appendChild(b);
  }
}
function renderBin() {
  chips($("#aKinds"), binKind, new Set(BIN.map((a) => a.kind)), (k) => { binKind = k; renderBin(); });
  const q = $("#aSearch").value.trim().toLowerCase();
  const list = BIN.filter((a) => (!binKind || a.kind === binKind) && (!q || `${a.name} ${a.path || a.block} ${a.kind} ${a.sub || ""}`.toLowerCase().includes(q)));
  const grid = $("#aGrid"); grid.innerHTML = "";
  if (!BIN.length) grid.innerHTML = '<div class="empty">Your bin is empty.<br>Drop files from your PC here, or use <b>＋ Add from library</b>.</div>';
  else if (!list.length) grid.innerHTML = '<div class="empty">Nothing matches.</div>';
  for (const a of list) grid.appendChild(assetTile(a, "bin"));
}
$("#aSearch").oninput = renderBin;
$("#aBig").onclick = () => { document.body.classList.toggle("bigAssets"); $("#aBig").classList.toggle("on", document.body.classList.contains("bigAssets")); };

// ---- the whole library (52k items): search, add to your bin, or drag straight in
$("#aAdd").onclick = () => { $("#libModal").classList.remove("hidden"); $("#libSearch").focus(); if (!$("#libGrid").children.length) searchLib(); };
$("#libClose").onclick = () => { $("#libModal").classList.add("hidden"); qvHide(); };
$("#libSearch").oninput = () => { clearTimeout(libTimer); libTimer = setTimeout(searchLib, 220); };
async function searchLib() {
  chips($("#libKinds"), libKind, null, (k) => { libKind = k; searchLib(); });
  const q = $("#libSearch").value.trim(), kind = libKind;
  const list = await api(`/api/assets?q=${enc(q)}&kind=${kind}&n=200`);
  if (q !== $("#libSearch").value.trim() || kind !== libKind) return;
  const grid = $("#libGrid"); grid.innerHTML = "";
  if (!list.length) grid.innerHTML = '<div class="empty">Nothing found.</div>';
  for (const a of list) grid.appendChild(assetTile(a, "lib"));
}
async function addToBin(items) { BIN = await post("/api/bin/add", { items }); renderBin(); }

// ---- tiles
function assetTile(a, where) {
  const el = document.createElement("div"); el.className = "at " + a.kind + (SEL.has(keyOf(a)) ? " sel" : ""); el.draggable = true;
  el.dataset.key = keyOf(a);
  el.innerHTML = '<div class="th"></div><div class="nm"></div><div class="sb"></div><span class="ck" title="Select for Make a video (or Ctrl+click)"></span>';
  const th = el.querySelector(".th"), src = thumbOf(a);
  if (src) { const im = new Image(); im.loading = "lazy"; im.draggable = false; im.src = src; im.onerror = () => { th.textContent = ICON[a.kind] || "📄"; }; th.appendChild(im); }
  else if (a.kind === "effect") { th.innerHTML = '<div class="fx">✨<br><span></span></div>'; th.querySelector("span").textContent = a.sub || "effect"; }
  else if (a.kind === "font") th.innerHTML = `<span class="fs" style="font-family:${fontFam(a)}">أبجد Abc</span>`;
  else if (a.kind === "lut" && S.path) {
    const im = new Image(); im.loading = "lazy"; im.draggable = false;
    im.src = `/api/lookpreview?path=${enc(S.path)}&t=${video.currentTime.toFixed(3)}&lut=${enc(a.lut || a.name)}&h=160`; th.appendChild(im);
  } else th.textContent = ICON[a.kind] || "📄";
  el.querySelector(".nm").textContent = a.name;
  el.querySelector(".sb").textContent = [a.sub, a.dur ? `${Math.round(a.dur)} s` : ""].filter(Boolean).join(" · ") || a.kind;
  if (AUDIO.has(a.kind) && a.path) { const b = document.createElement("span"); b.className = "play"; b.textContent = "▶"; el.appendChild(b); }
  if (a.restricted) { const l = document.createElement("span"); l.className = "lock"; l.textContent = "🔒"; l.title = "Free to use in your videos, but this file can't be shared"; el.appendChild(l); }
  if (where === "bin") {
    const x = document.createElement("span"); x.className = "rmv"; x.textContent = "✕"; x.title = "Remove from your bin";
    x.onclick = (e) => { e.stopPropagation(); removeFromBin(a); };
    el.appendChild(x);
  } else if (where === "lib") {
    const p = document.createElement("span"); p.className = "addb"; p.title = "Add to your bin";
    const inBin = () => BIN.some((b) => keyOf(b) === keyOf(a));
    p.textContent = inBin() ? "✓" : "＋";
    p.onclick = async (e) => {
      e.stopPropagation();
      if (!inBin()) { await addToBin([a]); p.textContent = "✓"; }
      if (MODE === "make") { if (!SEL.has(keyOf(a))) toggleSel(a); renderMakeBin(); }
    };
    el.appendChild(p);
  }
  el.querySelector(".ck").onclick = (e) => { e.stopPropagation(); toggleSel(a); };
  if (where === "pick" && AUDIO.has(a.kind) && a.path) {
    const pb = el.querySelector(".play"); pb.classList.add("live"); pb.title = "Listen";
    pb.onclick = (e) => { e.stopPropagation(); playAsset(a, el); };
  }
  el.onclick = (e) => {
    if (where === "pick" || e.ctrlKey || e.shiftKey || e.metaKey) return toggleSel(a);
    if (AUDIO.has(a.kind) && a.path) playAsset(a, el);                 // click a sound = play / stop
  };
  el.onmouseenter = () => qvShow(a, el);
  el.onmouseleave = qvHide;
  el.addEventListener("dragstart", (e) => {
    qvHide(); e.dataTransfer.setData("text/rr-asset", JSON.stringify(a)); e.dataTransfer.effectAllowed = "copy";
    setTimeout(() => document.body.classList.add("dragAsset"), 0);     // fade the big grid so the video can take the drop
  });
  el.addEventListener("dragend", () => document.body.classList.remove("dragAsset"));
  return el;
}

const AUD = new Audio(); let audEl = null;
function stopAud() { AUD.pause(); if (audEl) { audEl.classList.remove("playing"); const b = audEl.querySelector(".play"); if (b) b.textContent = "▶"; audEl = null; } }
function playAsset(a, el) {
  if (audEl === el) return stopAud();
  stopAud(); AUD.src = `/api/asset?path=${enc(a.path)}`; AUD.volume = 0.8; AUD.play();
  audEl = el; el.classList.add("playing"); const b = el.querySelector(".play"); if (b) b.textContent = "■";
}
AUD.onended = stopAud;

// ---- quick view on hover
let qvTimer = null;
function qvShow(a, el) { clearTimeout(qvTimer); qvTimer = setTimeout(() => openQv(a, el), 280); }
function qvHide() {
  clearTimeout(qvTimer); qvTimer = null;
  const q = $("#qv"); const v = q.querySelector("video"); if (v) { v.pause(); v.removeAttribute("src"); v.load(); }
  q.classList.add("hidden"); q.innerHTML = "";
}
function openQv(a, el) {
  const q = $("#qv"); q.innerHTML = ""; q.className = "qv-" + a.kind;
  const body = document.createElement("div"); body.className = "qb"; q.appendChild(body);
  const big = (tag, props) => Object.assign(document.createElement(tag), props);
  if (a.kind === "footage" || a.kind === "video") {
    body.appendChild(big("video", { src: a.kind === "video" ? `/media?path=${enc(a.path)}` : `/api/asset?path=${enc(a.path)}`, autoplay: true, muted: true, loop: true, playsInline: true }));
  } else if (VISUAL.has(a.kind) && a.path) body.appendChild(big("img", { src: `/api/asset?path=${enc(a.path)}` }));
  else if (a.kind === "font") body.innerHTML = `<div class="fbig" style="font-family:${fontFam(a)}">أبجد هوز حطي كلمن<br>صناعة الفيديو 123<br>The quick brown fox</div>`;
  else if (a.kind === "lut" && S.path) body.appendChild(big("img", { src: `/api/lookpreview?path=${enc(S.path)}&t=${video.currentTime.toFixed(3)}&lut=${enc(a.lut || a.name)}&h=480` }));
  else if (AUDIO.has(a.kind) && a.path) {
    const cv = big("canvas", { width: 360, height: 80 }); body.appendChild(cv);
    api(`/api/peaks?path=${enc(a.path)}`).then((j) => {
      const g = cv.getContext("2d"), P = j.p || []; g.fillStyle = "#5fd3a8";
      if (!P.length) { g.fillStyle = "#8b919c"; g.fillText("no waveform", 10, 40); return; }
      for (let x = 0; x < 360; x++) {
        const a0 = Math.floor((x / 360) * P.length), a1 = Math.max(a0 + 1, Math.floor(((x + 1) / 360) * P.length));
        let m = 0; for (let i = a0; i < a1; i++) if (P[i] > m) m = P[i];
        const h = Math.max(0.5, Math.sqrt(m / 255) * 38); g.fillRect(x, 40 - h, 1, h * 2);
      }
    });
    body.appendChild(big("div", { className: "qhint", textContent: "click the tile to play / stop" }));
  } else if (a.kind === "effect") body.appendChild(big("div", { className: "qdesc", textContent: a.desc || "HyperFrames effect" }));
  else body.appendChild(big("div", { className: "qicon", textContent: ICON[a.kind] || "📄" }));
  const meta = big("div", { className: "qm" });
  meta.appendChild(big("b", { textContent: a.name }));
  meta.appendChild(big("div", { textContent: [a.kind === "effect" ? `HyperFrames ${a.sub || "block"}: ${a.block}` : a.path, a.dur ? `${Math.round(a.dur)} s` : ""].filter(Boolean).join(" · ") }));
  q.appendChild(meta);
  const r = el.getBoundingClientRect(), W = 380;
  const side = el.closest("#library") && !document.body.classList.contains("bigAssets");   // small sidebar: open beside it
  const right = side ? $("#library").getBoundingClientRect().right : r.right;
  q.style.left = (right + 12 + W < innerWidth ? right + 12 : Math.max(8, r.left - 12 - W)) + "px";
  q.style.top = Math.max(50, Math.min(innerHeight - 420, r.top - 20)) + "px";
  q.classList.remove("hidden");
}

// ---- selection: videos, assets, effects, sounds -> "Make a video"
const SEL = new Map();
function toggleSel(a) {
  const k = keyOf(a);
  if (SEL.has(k)) SEL.delete(k); else SEL.set(k, { kind: a.kind, path: a.path || null, block: a.block || null, name: a.name, sub: a.sub || null });
  renderSel();
}
function renderSel() {
  document.querySelectorAll("[data-key]").forEach((el) => el.classList.toggle("sel", SEL.has(el.dataset.key)));
  $("#mkCompose").classList.toggle("hidden", !SEL.size);
  $("#selCount").textContent = SEL.size ? `${SEL.size} selected` : "";
  const box = $("#selList"); box.innerHTML = "";
  for (const [k, a] of SEL) {
    const c = document.createElement("span"); c.className = "sc"; c.textContent = `${ICON[a.kind] || "📎"} ${a.name}`; c.title = a.path || a.block;
    const x = document.createElement("b"); x.textContent = "✕"; x.onclick = () => { SEL.delete(k); renderSel(); };
    c.appendChild(x); box.appendChild(c);
  }
  updateTray();
  if (typeof renderMakeItems === "function" && MODE === "make") renderMakeItems();
}
$("#selClear").onclick = () => { SEL.clear(); renderSel(); };
$("#mkGo").onclick = async () => {
  if (!SEL.size) return;
  const text = $("#mkText").value.trim();
  if (!confirm(`${ENGINE_LABEL()} will make a NEW video from ${SEL.size} selected item${SEL.size > 1 ? "s" : ""}${text ? "" : " and decide everything itself (no instructions given)"}. It runs in the background; nothing existing is changed. Start?`)) return;
  const n = await post("/api/create", { items: [...SEL.values()], text, fmt: $("#mkFmt").value, level: $("#mkLevel").value, style: STYLE.tray, engine: ENGINE, noslop: NOSLOP });
  $("#mkText").value = ""; SEL.clear(); renderSel(); openLog(n.id); loadCreations();
};

let CREATIONS = [];
const CLABEL = { queued: "queued", running: "Claude is making it…", created: "ready ✓", failed: "failed", done: "finished (no video)", cancelled: "stopped", draft: "not started" };
async function loadCreations() {
  try { CREATIONS = await api("/api/creations"); } catch (e) { return; }
  for (const box of [$("#creations"), $("#creations2")]) {
  box.innerHTML = "";
  if (box.id === "creations2" && !CREATIONS.length) box.innerHTML = '<div class="muted">Nothing yet. Your videos appear here while Claude makes them.</div>';
  for (const n of CREATIONS) {
    const r = document.createElement("div"); r.className = "cr";
    r.innerHTML = `<div class="ct"><span class="st ${n.status === "created" ? "review" : n.status}"></span><span class="cx"></span></div><div class="acts"></div>`;
    r.querySelector(".st").textContent = CLABEL[n.status] || n.status;
    r.querySelector(".cx").textContent = `${n.engine === "codex" ? "Codex" : "Claude"} · ` + (n.text || "(AI decides)") + ` · ${(n.items || []).length} items`;
    r.title = (n.items || []).map((i) => i.name).join(", ") + (n.summary ? "\n\n" + n.summary : "");
    const acts = r.querySelector(".acts");
    const b = (label, fn, cls = "ghost small") => { const x = document.createElement("button"); x.className = cls; x.textContent = label; x.onclick = fn; acts.appendChild(x); };
    b("Progress", () => openLog(n.id));
    if (n.result) b("Open ▶", () => { setMode("editor"); showTab(false); loadVideos().then(() => openVideo(n.result)); }, "primary small");
    if (["failed", "done", "cancelled", "draft"].includes(n.status)) b("Run again", () => post(`/api/notes/${n.id}/send`).then(() => { openLog(n.id); loadCreations(); }));
    if (!["queued", "running"].includes(n.status)) b("✕", () => deleteNote(n));
    box.appendChild(r);
  }
  }
  updateTray();
}
function updateTray() {
  $("#tray").classList.toggle("hidden", !SEL.size && !CREATIONS.length);
  $("#crHead").classList.toggle("hidden", !CREATIONS.length);
}
setInterval(() => { if (!document.hidden) loadCreations(); }, 3000);

// ---- drop targets: the picture (a place + the current time), the timeline (a time), your bin (files from the PC)
function relPoint(e) { const r = ov.getBoundingClientRect(); return [clamp01((e.clientX - r.left) / r.width), clamp01((e.clientY - r.top) / r.height)]; }
const isDrag = (e) => [...e.dataTransfer.types].some((t) => t === "text/rr-asset" || t === "Files");
function dropHint(e, where) {
  const h = $("#dropHint");
  if (where === "picture") { const p = relPoint(e); h.textContent = `place here · ${Math.round(p[0] * 100)}%, ${Math.round(p[1] * 100)}% · ${tc(video.currentTime)}`; }
  else if (where === "timeline") h.textContent = `at ${tc(tlTime(e))}`;
  else h.textContent = "add to your bin";
  h.style.left = e.clientX + 16 + "px"; h.style.top = e.clientY + 16 + "px"; h.classList.remove("hidden");
}
async function uploadFile(f) {
  $("#dropHint").textContent = `copying ${f.name}…`;
  const r = await fetch("/api/upload", { method: "POST", headers: { "X-Name": encodeURIComponent(f.name) }, body: f });
  return r.json();
}
async function droppedItems(e) {
  const raw = e.dataTransfer.getData("text/rr-asset");
  if (raw) return [JSON.parse(raw)];
  const out = [];
  for (const f of e.dataTransfer.files) out.push(await uploadFile(f));
  return out;
}
let lastHover = -1;
for (const [zone, where] of [[$("#stageWrap"), "picture"], [$("#timeline"), "timeline"], [$("#assetsPane"), "bin"]]) {
  zone.addEventListener("dragover", (e) => {
    if (!isDrag(e) || (where !== "bin" && !S.info)) return;
    if (where === "bin" && ![...e.dataTransfer.types].includes("Files")) {
      const raw = [...e.dataTransfer.types].includes("text/rr-asset");
      if (!raw) return;                                            // the bin takes files and videos from the list
    }
    e.preventDefault(); e.dataTransfer.dropEffect = "copy"; zone.classList.add("dropping"); dropHint(e, where);
    if (where === "timeline") { const t = tlTime(e), f = frameOf(t); if (f !== lastHover) { lastHover = f; video.pause(); seek(t); } }
  });
  zone.addEventListener("dragleave", (e) => { if (!zone.contains(e.relatedTarget)) { zone.classList.remove("dropping"); $("#dropHint").classList.add("hidden"); } });
  zone.addEventListener("drop", async (e) => {
    e.preventDefault(); e.stopPropagation(); zone.classList.remove("dropping"); document.body.classList.remove("dragAsset");
    const pos = where === "picture" ? relPoint(e) : null, t = where === "timeline" ? tlTime(e) : video.currentTime;
    const items = await droppedItems(e);
    $("#dropHint").classList.add("hidden"); lastHover = -1;
    if (where === "bin") { const own = items.filter((a) => a.path && !a.mine); if (own.length) await addToBin(own); return loadBin(); }
    items.forEach((a, k) => placeAsset(a, pos && [clamp01(pos[0] + k * 0.05), clamp01(pos[1] + k * 0.05)], t));
    if (items.length) addToBin(items);                               // whatever you use lands in your bin
  });
}
window.addEventListener("dragover", (e) => e.preventDefault());   // a file dropped elsewhere must not open in the window
window.addEventListener("drop", (e) => { e.preventDefault(); document.body.classList.remove("dragAsset"); });

function placeAsset(a, pos, t) {
  const small = a.kind === "icon" || a.kind === "emoji";
  const d = { kind: a.kind, path: a.path || null, block: a.block || null, name: a.name, sub: a.sub || null, lut: a.lut || null,
    x: pos ? pos[0] : null, y: pos ? pos[1] : null, w: pos && VISUAL.has(a.kind) ? (small ? 0.18 : 0.35) : null, t, thumb: thumbOf(a) };
  if (d.thumb) dimg(d.thumb);
  remember("add " + a.name);
  S.drops.push(d); video.pause(); renderDrops();
  const ta = $("#noteText"); ta.focus();
  if (!ta.value.trim()) ta.placeholder = `What should happen with "${a.name}" here?  ماذا أفعل به هنا؟`;
}
function renderDrops() { drawOverlay(); drawMarkers(); listDrops(); }

let moving = null;
function addDrops() {                                              // placed assets on the picture: drag to move, wheel to resize
  S.drops.forEach((d, i) => {
    if (d.x == null) return;
    const vis = d.w && d.thumb;
    const el = document.createElement("div"); el.className = "drop " + (vis ? "vis" : "chip");
    el.style.left = d.x * 100 + "%"; el.style.top = d.y * 100 + "%";
    el.title = "drag to move" + (vis ? " · mouse wheel to resize" : "");
    if (vis) { el.style.width = d.w * 100 + "%"; const im = new Image(); im.src = d.thumb; im.draggable = false; el.appendChild(im); }
    else el.append(`${ICON[d.kind] || "📎"} ${d.name}`);
    const lbl = document.createElement("span"); lbl.className = "lbl"; lbl.textContent = `${i + 1}  ${vis ? d.name : ""}`.trim(); el.appendChild(lbl);
    const x = document.createElement("span"); x.className = "x"; x.textContent = "✕"; x.title = "Remove"; el.appendChild(x);
    x.onmousedown = (e) => e.stopPropagation();
    x.onclick = (e) => { e.stopPropagation(); remember("remove " + d.name); S.drops.splice(i, 1); S.selDrop = null; renderDrops(); };
    if (S.selDrop === i) el.classList.add("picked");
    el.addEventListener("mousedown", (e) => {
      e.stopPropagation(); e.preventDefault(); video.pause();
      remember("move " + d.name); S.selDrop = i;
      moving = { d, sx: e.clientX, sy: e.clientY, x: d.x, y: d.y }; drawOverlay();
    });
    el.addEventListener("wheel", (e) => {
      if (!d.w) return;
      e.preventDefault(); e.stopPropagation();
      if (Date.now() - (S.lastResize || 0) > 700) remember("resize " + d.name);
      S.lastResize = Date.now();
      d.w = Math.max(0.03, Math.min(1.2, d.w * Math.exp(-e.deltaY * 0.0015))); drawOverlay(); listDrops();
    }, { passive: false });
    ov.appendChild(el);
  });
}
window.addEventListener("mousemove", (e) => {
  if (!moving) return;
  const r = ov.getBoundingClientRect();
  moving.d.x = clamp01(moving.x + (e.clientX - moving.sx) / r.width); moving.d.y = clamp01(moving.y + (e.clientY - moving.sy) / r.height);
  drawOverlay();
});
window.addEventListener("mouseup", () => { if (moving) { moving = null; listDrops(); } });

function listDrops() {
  const box = $("#cDrops"); box.innerHTML = "";
  S.drops.forEach((d, i) => {
    const r = document.createElement("div"); r.className = "dr";
    r.innerHTML = '<span class="n"></span><span class="nm"></span><span class="tm" title="Go to this time"></span><span class="rm" title="Remove">✕</span>';
    r.querySelector(".n").textContent = i + 1;
    r.querySelector(".nm").textContent = `${ICON[d.kind] || "📎"} ${d.name}` + (d.x != null
      ? ` · ${Math.round(d.x * 100)}%, ${Math.round(d.y * 100)}%` + (d.w ? ` · ${Math.round(d.w * 100)}% wide` : "") : " · on the timeline");
    r.title = d.path || `HyperFrames ${d.sub || "block"}: ${d.block}`;
    r.querySelector(".tm").textContent = tc(d.t);
    r.querySelector(".tm").onclick = () => { video.pause(); seek(d.t); };
    r.querySelector(".rm").onclick = () => { remember("remove " + d.name); S.drops.splice(i, 1); S.selDrop = null; renderDrops(); };
    box.appendChild(r);
  });
}

function burnDrops(g, w, h, lw) {                                 // draw the placed assets on the frame image Claude reads
  S.drops.forEach((d, i) => {
    if (d.x == null) return;
    const cx = d.x * w, cy = d.y * h, im = d.thumb && d.w ? DIMG[d.thumb] : null;
    let bw, bh;
    if (im && im.naturalWidth) {
      bw = d.w * w; bh = (bw * im.naturalHeight) / im.naturalWidth;
      g.globalAlpha = 0.92; g.drawImage(im, cx - bw / 2, cy - bh / 2, bw, bh); g.globalAlpha = 1;
    } else {
      g.font = `bold ${Math.round(w / 30)}px Segoe UI`; bw = g.measureText(d.name).width + w / 25; bh = w / 16;
      g.fillStyle = "rgba(58,45,92,.9)"; g.fillRect(cx - bw / 2, cy - bh / 2, bw, bh);
      g.fillStyle = "#fff"; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(d.name, cx, cy);
    }
    g.setLineDash([lw * 3, lw * 2]); g.strokeStyle = "#b48cff"; g.lineWidth = lw; g.strokeRect(cx - bw / 2, cy - bh / 2, bw, bh); g.setLineDash([]);
    const R = Math.max(14, w / 45), lx = cx - bw / 2, ly = cy - bh / 2;
    g.fillStyle = "#b48cff"; g.beginPath(); g.arc(lx, ly, R, 0, 7); g.fill();
    g.fillStyle = "#160d2b"; g.font = `bold ${Math.round(R * 1.2)}px Segoe UI`; g.textAlign = "center"; g.textBaseline = "middle";
    g.fillText(String(i + 1), lx, ly);
    g.textAlign = "start"; g.textBaseline = "alphabetic";
  });
}
loadCreations();


// ---------------------------------------------------------------- standalone: drop videos into the list; disable what is not installed
(function () {
  post("/api/caps").then((c) => {
    if (!c.whisper) for (const id of ["#micBtn", "#txBtn"]) {
      const b = $(id); b.disabled = true; b.title = "Speech is not installed on this PC: run Setup.bat and choose the speech option.";
    }
    if (!c.ffmpeg) alert("ffmpeg is not installed on this PC. Run Setup.bat (in the Review Room folder) first.");
  });
})();

// ---------------------------------------------------------------- start screen: Make a video / Editor mode
let MODE = "home";
function setMode(m) {
  MODE = m;
  $("#home").classList.toggle("hidden", m !== "home");
  $("#makePage").classList.toggle("hidden", m !== "make");
  document.querySelector("main").classList.toggle("hidden", m !== "editor");
  $("#homeBtn").classList.toggle("hidden", m === "home");
  document.querySelector("header .hint").classList.toggle("hidden", m !== "editor");
  qvHide(); stopAud();
  if (m === "editor") { layout(); loadBin(); }
  if (m === "make") { renderMakeBin(); renderMakeItems(); loadCreations(); }
  if (m === "home") renderHome();
}
$("#goMake").onclick = () => setMode("make");
$("#goEdit").onclick = () => setMode("editor");
$("#homeBtn").onclick = () => setMode("home");

async function renderHome() {
  const [vids, bin, all] = await Promise.all([api("/api/videos"), api("/api/bin"), api("/api/notes")]);
  S.videos = vids;
  const busy = all.running ? 1 + (all.queued || 0) : 0;
  const cs = $("#claudeState");
  cs.textContent = !all.claude ? "Claude CLI missing" : busy ? "Claude working" : "Claude ready";
  cs.className = "pill " + (!all.claude ? "bad" : busy ? "busy" : "ok");
  const st = $("#hStatus"); st.innerHTML = "";
  const part = (txt, cls) => { const b = document.createElement("b"); b.textContent = txt; if (cls) b.className = cls; return b; };
  st.append(part(vids.length), ` video${vids.length === 1 ? "" : "s"}  ·  `, part(bin.length), ` in your bin  ·  `,
    !all.claude ? part("Claude Code is not installed: run Setup.bat") : busy ? part(`Claude is working (${busy} job${busy > 1 ? "s" : ""})`, "on") : "Claude is ready");
  const box = $("#hRecent"); box.innerHTML = "";
  const recent = [...vids].sort((a, b) => b.mtime - a.mtime).slice(0, 8);
  if (!recent.length) { box.innerHTML = '<p class="hNone">No videos yet. Make one, or drop video files into the editor.</p>'; return; }
  for (const v of recent) {
    const b = document.createElement("button"); b.className = "hRec"; b.title = `Open ${v.name} in the editor`;
    const im = new Image(); im.alt = ""; im.src = `/api/poster?path=${enc(v.path)}`;
    const n = document.createElement("span"); n.className = "n"; n.textContent = v.name;
    const m = document.createElement("span"); m.className = "m"; m.textContent = v.kind === "render" ? "made by Claude" : "video";
    b.append(im, n, m); box.appendChild(b);
    b.onclick = () => { setMode("editor"); showTab(false); openVideo(v.path); };
    api(`/api/info?path=${enc(v.path)}`).then((i) => {
      const s = Math.round(i.duration || 0); m.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}  ·  ${i.width}×${i.height}` + (v.kind === "render" ? "  ·  made by Claude" : "");
    });
  }
}

// ---------------------------------------------------------------- edit level: normal / heavy
const LEVEL_INFO = {
  normal: "Normal: simple colour correction and captions, no 3D. Claude Opus 5.5 on medium effort. Quicker.",
  heavy: "Heavy: Claude studies the video, searches the web for assets, can use 3D (Blender), and aims for a professional video. Claude Opus 5.5 on high effort. Slower, uses more of your plan.",
};
let CAPS = {};
function levelHint(sel, out) {
  const v = sel.value;
  const who = ENGINE === "codex" ? `Codex ${CAPS.codex_model || ""}`.trim() : "Claude Opus 5.5";
  let t = LEVEL_INFO[v].replace("Claude Opus 5.5", who);
  if (v === "heavy" && CAPS.blender === false) t += " (Blender is not installed: run Setup.bat to add 3D.)";
  if (out) out.textContent = t;
  sel.title = t;
}
for (const id of ["#levelSel", "#mkLevel", "#mkLevel2"]) $(id).onchange = () => levelHint($(id), id === "#mkLevel2" ? $("#mkLevelInfo") : null);

// ---------------------------------------------------------------- the Make a video page
function renderMakeItems() {
  const box = $("#mkItems"); box.innerHTML = "";
  $("#mkDrop").classList.toggle("has", SEL.size > 0);
  for (const [k, a] of SEL) {
    const c = document.createElement("div"); c.className = "mki"; c.title = a.path || a.block || a.lut || "";
    const th = document.createElement("div"); th.className = "th";
    const src = thumbOf(a);
    if (src) { const im = new Image(); im.src = src; im.draggable = false; th.appendChild(im); } else th.textContent = ICON[a.kind] || "📎";
    const nm = document.createElement("div"); nm.className = "nm"; nm.textContent = a.name;
    const x = document.createElement("b"); x.className = "x"; x.textContent = "✕"; x.title = "Remove";
    x.onclick = () => { SEL.delete(k); renderSel(); };
    c.append(th, nm, x); box.appendChild(c);
  }
  $("#mkCount").textContent = SEL.size ? `${SEL.size} item${SEL.size > 1 ? "s" : ""}` : "nothing yet";
}
async function renderMakeBin() {
  if (!S.videos.length) S.videos = await api("/api/videos");
  BIN = await api("/api/bin");
  const grid = $("#mkBinGrid"); grid.innerHTML = "";
  const head = (t) => { const h = document.createElement("div"); h.className = "mkHead"; h.textContent = t; grid.appendChild(h); };
  head(`Your videos (${S.videos.length})`);
  if (!S.videos.length) grid.insertAdjacentHTML("beforeend", '<div class="empty">No videos yet: drop them on the left.</div>');
  for (const v of S.videos) grid.appendChild(assetTile({ kind: "video", path: v.path, name: v.name, sub: v.kind === "render" ? "made by Claude" : "" }, "pick"));
  head(`Your bin (${BIN.length})`);
  if (!BIN.length) grid.insertAdjacentHTML("beforeend", '<div class="empty">Your bin is empty: drop files on the left, or ＋ Library.</div>');
  for (const a of BIN) grid.appendChild(assetTile(a, "pick"));
}
$("#mkLib").onclick = () => $("#aAdd").click();
$("#mkGo2").onclick = async () => {
  const text = $("#mkDesc").value.trim();
  if (!SEL.size && !text) { $("#mkDesc").focus(); return alert("Drop or pick something, or describe the video you want."); }
  const level = $("#mkLevel2").value;
  const what = SEL.size ? `from ${SEL.size} item${SEL.size > 1 ? "s" : ""}` : "from your description only (an animation or a 3D video)";
  if (!confirm(`${ENGINE_LABEL()} will make a NEW video ${what}, as a ${level} edit${text ? "" : ", deciding everything itself"}. It runs in the background. Start?`)) return;
  const n = await post("/api/create", { items: [...SEL.values()], text, fmt: $("#mkFmt2").value, level, style: STYLE.make, engine: ENGINE, noslop: NOSLOP });
  $("#mkDesc").value = ""; SEL.clear(); renderSel(); openLog(n.id); loadCreations();
};
$("#mkMic").onclick = () => dictate($("#mkMic"), $("#mkDesc"));
$("#micBtn").onclick = () => dictate($("#micBtn"), $("#noteText"));

// dictation into any text box (replaces the editor-only version)
let rec2 = null;
async function dictate(btn, ta) {
  if (rec2) { rec2.stop(); return; }
  post("/api/warm");
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
  catch (err) { alert("The microphone is not available: allow it for this app and try again.\n" + err); return; }
  const chunks = [], label = btn.textContent;
  rec2 = new MediaRecorder(stream);
  rec2.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  rec2.onstop = async () => {
    stream.getTracks().forEach((t) => t.stop()); rec2 = null;
    btn.classList.remove("rec"); btn.textContent = "… writing"; btn.disabled = true;
    try {
      const url = await new Promise((ok) => { const r = new FileReader(); r.onload = () => ok(r.result); r.readAsDataURL(new Blob(chunks, { type: "audio/webm" })); });
      const j = await post("/api/dictate", { audio: url });
      if (j.error) alert("Could not transcribe: " + j.error);
      else if (j.text) { ta.value = (ta.value.trim() ? ta.value.trim() + " " : "") + j.text.trim(); ta.focus(); }
    } finally { btn.disabled = false; btn.textContent = label; }
  };
  rec2.start(); btn.classList.add("rec"); btn.textContent = "■ Stop";
}

// ---------------------------------------------------------------- drop rules: what each place accepts
const VIDEO_EXT = /\.(mp4|mov|webm|mkv|m4v|avi)$/i;
function refuse(e, msg) {
  e.preventDefault(); e.dataTransfer.dropEffect = "none";
  const h = $("#dropHint"); h.textContent = "⛔ " + msg; h.classList.add("bad"); h.classList.remove("hidden");
  h.style.left = e.clientX + 16 + "px"; h.style.top = e.clientY + 16 + "px";
}
function fileKinds(e) {                                            // during a drag only MIME types are known (names come on drop)
  return [...e.dataTransfer.items].filter((i) => i.kind === "file").map((i) => i.type || "");
}
async function uploadTo(f, dest) {
  const r = await fetch("/api/upload", { method: "POST", headers: { "X-Name": encodeURIComponent(f.name), ...(dest ? { "X-Dest": dest } : {}) }, body: f });
  return r.json();
}
// the video list takes video files only
(function () {
  const pane = $("#videosPane");
  pane.addEventListener("dragover", (e) => {
    const t = [...e.dataTransfer.types];
    if (t.includes("text/rr-asset")) return refuse(e, "Only videos here. Photos, sounds and effects go to Assets & effects.");
    if (!t.includes("Files")) return;
    const bad = fileKinds(e).filter((m) => m && !m.startsWith("video/"));
    if (bad.length) return refuse(e, "Only videos here. Photos, sounds and other files go to Assets & effects.");
    e.preventDefault(); e.dataTransfer.dropEffect = "copy"; pane.classList.add("dropping");
    const h = $("#dropHint"); h.classList.remove("bad"); h.textContent = "add to your videos"; h.classList.remove("hidden");
    h.style.left = e.clientX + 16 + "px"; h.style.top = e.clientY + 16 + "px";
  }, true);
  pane.addEventListener("dragleave", (e) => { if (!pane.contains(e.relatedTarget)) { pane.classList.remove("dropping"); $("#dropHint").classList.add("hidden"); } });
  pane.addEventListener("drop", async (e) => {
    e.preventDefault(); e.stopImmediatePropagation(); pane.classList.remove("dropping"); $("#dropHint").classList.add("hidden");
    if ([...e.dataTransfer.types].includes("text/rr-asset")) return;
    const files = [...e.dataTransfer.files], ok = files.filter((f) => VIDEO_EXT.test(f.name)), skipped = files.length - ok.length;
    let last = null;
    for (const f of ok) last = (await uploadTo(f, "videos")).path;
    if (skipped) toast(`Skipped ${skipped} file${skipped > 1 ? "s" : ""} that ${skipped > 1 ? "are" : "is"} not a video (put photos and sounds in Assets & effects).`);
    await loadVideos(); if (last) openVideo(last);
  }, true);
})();
// the Make page takes anything: videos go to your videos, everything else to your bin; all of it is selected
(function () {
  const zone = $("#makePage");
  zone.addEventListener("dragover", (e) => {
    const t = [...e.dataTransfer.types];
    if (!t.includes("Files") && !t.includes("text/rr-asset")) return;
    e.preventDefault(); e.dataTransfer.dropEffect = "copy"; $("#mkDrop").classList.add("dropping");
  });
  zone.addEventListener("dragleave", (e) => { if (!zone.contains(e.relatedTarget)) $("#mkDrop").classList.remove("dropping"); });
  zone.addEventListener("drop", async (e) => {
    e.preventDefault(); e.stopPropagation(); $("#mkDrop").classList.remove("dropping");
    const raw = e.dataTransfer.getData("text/rr-asset");
    const items = raw ? [JSON.parse(raw)] : [];
    for (const f of e.dataTransfer.files) {
      $("#mkCount").textContent = `copying ${f.name}…`;
      items.push(await uploadTo(f, VIDEO_EXT.test(f.name) ? "videos" : null));
    }
    for (const a of items) { const k = keyOf(a.path && a.path.startsWith("videos/") ? { ...a, kind: "video" } : a); if (!SEL.has(k)) toggleSel(a.path && a.path.startsWith("videos/") ? { ...a, kind: "video" } : a); }
    S.videos = await api("/api/videos"); renderLibrary(); renderMakeBin();
  });
})();

// ---------------------------------------------------------------- undo / redo / delete
const HIST = { undo: [], redo: [] };
const snapLocal = () => JSON.stringify({ drops: S.drops, pin: S.pin, box: S.box, rin: S.rin, rout: S.rout });
function restoreLocal(js) {
  const o = JSON.parse(js);
  S.drops = o.drops; S.pin = o.pin; S.box = o.box; S.rin = o.rin; S.rout = o.rout; S.selDrop = null;
  for (const d of S.drops) if (d.thumb) dimg(d.thumb);
  drawOverlay(); updateSpot(); drawRange(); drawMarkers(); listDrops();
}
function remember(label) {
  HIST.undo.push({ kind: "local", label, state: snapLocal() });
  if (HIST.undo.length > 200) HIST.undo.shift();
  HIST.redo = [];
}
function pushAction(label, undoFn, redoFn) { HIST.undo.push({ kind: "action", label, undo: undoFn, redo: redoFn }); HIST.redo = []; }
async function undo() {
  const a = HIST.undo.pop(); if (!a) return toast("Nothing to undo");
  if (a.kind === "local") { HIST.redo.push({ kind: "local", label: a.label, state: snapLocal() }); restoreLocal(a.state); }
  else { await a.undo(); HIST.redo.push(a); }
  toast("Undo: " + a.label);
}
async function redo() {
  const a = HIST.redo.pop(); if (!a) return toast("Nothing to redo");
  if (a.kind === "local") { HIST.undo.push({ kind: "local", label: a.label, state: snapLocal() }); restoreLocal(a.state); }
  else { await a.redo(); HIST.undo.push(a); }
  toast("Redo: " + a.label);
}
function deleteSelected() {
  if (S.selDrop != null && S.drops[S.selDrop]) {
    const nm = S.drops[S.selDrop].name; remember("remove " + nm); S.drops.splice(S.selDrop, 1); S.selDrop = null; renderDrops();
    toast(`Removed ${nm} · Ctrl+Z to undo`);
  } else if (S.pin || S.box) { remember("clear the spot"); clearSpot(); toast("Spot cleared · Ctrl+Z to undo"); }
  else if (S.rin != null) { remember("clear the range"); S.rin = S.rout = null; drawRange(); toast("Range cleared · Ctrl+Z to undo"); }
  else toast("Nothing selected to delete (click a placed asset first)");
}
async function deleteNote(n) {
  await post(`/api/notes/${n.id}/delete`); await loadNotes(); loadCreations();
  pushAction("delete note", async () => { await post(`/api/notes/${n.id}/restore`); await loadNotes(); loadCreations(); },
    async () => { await post(`/api/notes/${n.id}/delete`); await loadNotes(); loadCreations(); });
  toast("Note deleted · Ctrl+Z to undo");
}
async function removeFromBin(a) {
  BIN = await post("/api/bin/remove", { id: a.id }); renderBin(); if (MODE === "make") renderMakeBin();
  const key = keyOf(a);
  pushAction("remove " + a.name + " from the bin", async () => { await addToBin([a]); if (MODE === "make") renderMakeBin(); },
    async () => { const b = BIN.find((x) => keyOf(x) === key); if (b) { BIN = await post("/api/bin/remove", { id: b.id }); renderBin(); } });
  toast(`Removed ${a.name} · Ctrl+Z to undo`);
}
window.addEventListener("keydown", (e) => {
  const typing = ["TEXTAREA", "INPUT", "SELECT"].includes(e.target.tagName);
  if (typing) return;                                              // text boxes keep their own Ctrl+Z
  const k = e.key.toLowerCase(), mod = e.ctrlKey || e.metaKey;
  if (mod && k === "z" && !e.shiftKey) { e.preventDefault(); e.stopImmediatePropagation(); undo(); }
  else if (mod && (k === "y" || (k === "z" && e.shiftKey))) { e.preventDefault(); e.stopImmediatePropagation(); redo(); }
  else if ((e.key === "Delete" || e.key === "Backspace") && MODE === "editor") { e.preventDefault(); e.stopImmediatePropagation(); deleteSelected(); }
  else if (MODE === "home" && !mod && (k === "m" || k === "e")) { e.preventDefault(); e.stopImmediatePropagation(); setMode(k === "m" ? "make" : "editor"); }
  else if (MODE !== "editor") e.stopImmediatePropagation();       // editor keys only work in the editor
}, true);

let toastTimer = null;
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.remove("hidden");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.add("hidden"), 2600);
}

// ---------------------------------------------------------------- start
post("/api/caps").then((c) => {
  CAPS = c;
  if (!c.whisper) { const b = $("#mkMic"); b.disabled = true; b.title = "Speech is not installed on this PC: run Setup.bat and choose the speech option."; }
  levelHint($("#mkLevel2"), $("#mkLevelInfo")); levelHint($("#levelSel")); levelHint($("#mkLevel"));
});
setMode("home");

// ---------------------------------------------------------------- folders: Default assets / Effects / Looks, browsable in the bin and on the Make page
const NAV = { panel: "", make: "" };                                // "" = the top level (your bin)
const ROOT_DIRS = [["assets/Default assets", "Default assets", "📁"], ["@effects", "Effects", "✨"], ["@looks", "Looks", "🎨"]];
const ROOT_SUB = { "assets/Default assets": "", "@effects": "", "@looks": "" };
api("/api/browse?dir=" + enc("assets/Default assets") + "&n=0").then((r) => {
  ROOT_SUB["assets/Default assets"] = `${r.dirs.length} folders · ${r.dirs.reduce((a, d) => a + d.count, 0).toLocaleString()} files`;
});
api("/api/browse?dir=@effects&n=0").then((r) => { ROOT_SUB["@effects"] = `${r.dirs.reduce((a, d) => a + d.count, 0)} HyperFrames effects`; });
api("/api/browse?dir=@looks&n=0").then((r) => { ROOT_SUB["@looks"] = `${r.total} colour looks`; });

function folderTile(name, sub, icon, open) {
  const el = document.createElement("div"); el.className = "at folder"; el.title = "Open " + name;
  el.innerHTML = '<div class="th"></div><div class="nm"></div><div class="sb"></div>';
  el.querySelector(".th").textContent = icon; el.querySelector(".nm").textContent = name; el.querySelector(".sb").textContent = sub;
  el.onclick = open;
  return el;
}
function crumbNames(dir) {
  if (!dir) return [];
  if (dir.startsWith("@effects")) return [["@effects", "Effects"], ...(dir.includes("/") ? [[dir, dir.split("/")[1].replace(/^./, (c) => c.toUpperCase()) + "s"]] : [])];
  if (dir === "@looks") return [["@looks", "Looks"]];
  const parts = dir.split("/").slice(1), out = [];                   // drop "assets"
  parts.forEach((p, i) => out.push(["assets/" + parts.slice(0, i + 1).join("/"), p]));
  return out;
}
function renderCrumbs(where, box) {
  box.innerHTML = "";
  const path = [["", where === "make" ? "Pick from" : "Your bin"], ...crumbNames(NAV[where])];
  path.forEach(([dir, name], i) => {
    const last = i === path.length - 1;
    const c = document.createElement(last ? "span" : "button"); c.className = last ? "cur" : "ghost small"; c.textContent = name;
    if (!last) c.onclick = () => go(where, dir);
    box.appendChild(c);
    if (!last) box.append(" › ");
  });
  box.classList.toggle("hidden", path.length === 1);
}
function go(where, dir) {
  NAV[where] = dir;
  if (where === "panel") { $("#aSearch").value = ""; renderBin(); } else { $("#mkSearch").value = ""; renderMakeBin(); }
}
async function renderFolder(where, grid) {
  const d = NAV[where], q = (where === "panel" ? $("#aSearch") : $("#mkSearch")).value.trim();
  const mode = where === "panel" ? "lib" : "pick";
  let dirs = [], items = [], total = 0;
  if (q) { items = await api(`/api/assets?q=${enc(q)}&dir=${enc(d)}&n=300`); total = items.length; }
  else { const r = await api(`/api/browse?dir=${enc(d)}&n=400`); dirs = r.dirs; items = r.items; total = r.total; }
  if (NAV[where] !== d) return;                                    // the user moved on meanwhile
  grid.innerHTML = "";
  for (const x of dirs) grid.appendChild(folderTile(x.name, `${x.count.toLocaleString()} file${x.count === 1 ? "" : "s"}`, "📁", () => go(where, x.dir)));
  for (const a of items) grid.appendChild(assetTile(a, mode));
  if (!dirs.length && !items.length) grid.innerHTML = `<div class="empty">${q ? "Nothing matches in this folder." : "This folder is empty."}</div>`;
  if (total > items.length) grid.insertAdjacentHTML("beforeend", `<div class="empty">Showing ${items.length} of ${total.toLocaleString()}. Type in the search box to find the rest.</div>`);
}
function rootFolders(where, grid) {
  for (const [dir, name, icon] of ROOT_DIRS) grid.appendChild(folderTile(name, ROOT_SUB[dir] || "", icon, () => go(where, dir)));
}

// the bin panel: the top level shows the folders, then your bin; inside a folder it browses
const _renderBinFlat = renderBin;
renderBin = function () {
  renderCrumbs("panel", $("#aCrumbs"));
  $("#aKinds").classList.toggle("hidden", !!NAV.panel);
  $("#aSearch").placeholder = NAV.panel ? "Search this folder…" : "Filter your bin…";
  if (NAV.panel) return renderFolder("panel", $("#aGrid"));
  _renderBinFlat();
  const grid = $("#aGrid"), first = grid.firstChild, frag = document.createDocumentFragment();
  rootFolders("panel", frag);
  if (grid.querySelector(".empty")) grid.querySelector(".empty").innerHTML = "Your bin is empty: open <b>Default assets</b>, drop files from your PC here, or use <b>＋ Add from library</b>.";
  grid.insertBefore(frag, first);
};
let aSearchTimer = null;
$("#aSearch").oninput = () => { clearTimeout(aSearchTimer); aSearchTimer = setTimeout(renderBin, NAV.panel ? 250 : 0); };

// the Make page: your videos, the folders, your bin; inside a folder it browses
const _renderMakeBinFlat = renderMakeBin;
renderMakeBin = async function () {
  renderCrumbs("make", $("#mkCrumbs"));
  if (NAV.make) return renderFolder("make", $("#mkBinGrid"));
  await _renderMakeBinFlat();
  const grid = $("#mkBinGrid"), heads = grid.querySelectorAll(".mkHead"), binHead = heads[1];
  const h = document.createElement("div"); h.className = "mkHead"; h.textContent = "Folders";
  const frag = document.createDocumentFragment(); frag.appendChild(h); rootFolders("make", frag);
  grid.insertBefore(frag, binHead);
};
let mkSearchTimer = null;
$("#mkSearch").oninput = () => {
  clearTimeout(mkSearchTimer);
  mkSearchTimer = setTimeout(() => {
    if (!NAV.make && $("#mkSearch").value.trim()) NAV.make = "assets/Default assets";   // searching from the top looks through Default assets
    renderMakeBin();
  }, 250);
};

// ---------------------------------------------------------------- edit styles
let STYLES = [];
const STYLE = { editor: "auto", tray: "auto", make: "auto" };
const STYLE_BTN = { editor: "#styleBtn", tray: "#mkStyleT", make: "#mkStyle2" };
api("/api/styles").then((list) => { STYLES = list; for (const w in STYLE_BTN) setStyle(w, STYLE[w]); });
function setStyle(where, id) {
  STYLE[where] = id;
  const st = STYLES.find((x) => x.id === id) || { name: "Auto", desc: "" };
  const b = $(STYLE_BTN[where]); b.innerHTML = ""; b.title = st.desc || "";
  if (st.img) { const im = new Image(); im.src = st.img; im.alt = ""; im.className = "stThumb"; b.appendChild(im); }
  b.append(`Style: ${st.name} ▾`);
}
let STYLE_TAB = "Edit footage";
function openStyles(where, btn) {
  const pop = $("#stylePop");
  if (!pop.classList.contains("hidden") && pop.dataset.for === where) return pop.classList.add("hidden");
  pop.dataset.for = where;
  const cur = STYLES.find((x) => x.id === STYLE[where]); if (cur) STYLE_TAB = cur.group;
  const groups = [...new Set(STYLES.map((x) => x.group))];
  const draw = () => {
    pop.innerHTML = "";
    const tabs = document.createElement("div"); tabs.className = "spTabs";
    for (const g of groups) {
      const t = document.createElement("button"); t.className = "ghost" + (g === STYLE_TAB ? " on" : "");
      t.textContent = `${g} · ${STYLES.filter((x) => x.group === g).length}`;
      t.onclick = (e) => { e.stopPropagation(); STYLE_TAB = g; draw(); };
      tabs.appendChild(t);
    }
    pop.appendChild(tabs);
    const grid = document.createElement("div"); grid.className = "spGrid"; pop.appendChild(grid);
    for (const st of STYLES.filter((x) => x.group === STYLE_TAB)) {
      const c = document.createElement("button"); c.className = "spCard" + (STYLE[where] === st.id ? " on" : ""); c.title = st.desc;
      const im = new Image(); im.src = st.img; im.alt = ""; im.loading = "lazy";
      const nm = document.createElement("b"); nm.textContent = st.name;
      const ds = document.createElement("span"); ds.className = "ds"; ds.textContent = st.desc;
      c.append(im, nm, ds);
      c.onclick = () => { setStyle(where, st.id); pop.classList.add("hidden"); };
      grid.appendChild(c);
    }
  };
  draw();
  const r = btn.getBoundingClientRect(), W = 780;
  pop.style.left = Math.max(8, Math.min(innerWidth - W - 8, r.left)) + "px";
  pop.classList.remove("hidden");
  const h = pop.getBoundingClientRect().height;
  pop.style.top = (r.bottom + 6 + h < innerHeight ? r.bottom + 6 : Math.max(50, r.top - 6 - h)) + "px";
}
for (const w in STYLE_BTN) $(STYLE_BTN[w]).onclick = (e) => { e.stopPropagation(); openStyles(w, e.currentTarget); };
document.addEventListener("click", (e) => { if (!e.target.closest("#stylePop")) $("#stylePop").classList.add("hidden"); });
window.addEventListener("keydown", (e) => { if (e.key === "Escape") $("#stylePop").classList.add("hidden"); });


// ---------------------------------------------------------------- engine: Claude or Codex (one choice, shown in three places)
let ENGINE = "claude";
try { ENGINE = localStorage.getItem("rr.engine") === "codex" ? "codex" : "claude"; } catch (e) { ENGINE = "claude"; }
const ENGINE_SELS = ["#engineSel", "#mkEngine", "#mkEngine2"];
const ENGINE_LABEL = () => (ENGINE === "codex" ? "Codex" : "Claude");
function setEngine(v) {
  ENGINE = v === "codex" ? "codex" : "claude";
  try { localStorage.setItem("rr.engine", ENGINE); } catch (e) { /* per-viewer convenience only */ }
  for (const id of ENGINE_SELS) $(id).value = ENGINE;
  levelHint($("#mkLevel2"), $("#mkLevelInfo")); levelHint($("#levelSel")); levelHint($("#mkLevel"));
}
for (const id of ENGINE_SELS) $(id).onchange = () => setEngine($(id).value);
post("/api/caps").then((c) => {
  Object.assign(CAPS, c);
  if (!c.codex) for (const id of ENGINE_SELS) {
    const o = $(id).querySelector('option[value="codex"]'); o.disabled = true; o.textContent = "Codex (not installed)";
  }
  setEngine(c.codex ? ENGINE : "claude");
});


// ---------------------------------------------------------------- "Remove AI slop audio" (one switch, shown on the Make page and in the tray)
let NOSLOP = false;
try { NOSLOP = localStorage.getItem("rr.noslop") === "1"; } catch (e) { NOSLOP = false; }
function setNoSlop(on) {
  NOSLOP = !!on;
  try { localStorage.setItem("rr.noslop", NOSLOP ? "1" : "0"); } catch (e) { /* per-viewer convenience only */ }
  for (const id of ["#noSlop2", "#noSlopT"]) {
    const b = $(id); b.classList.toggle("on", NOSLOP); b.setAttribute("aria-pressed", String(NOSLOP));
    b.textContent = NOSLOP ? "✓ AI slop audio removed" : "🔇 Remove AI slop audio";
  }
}
for (const id of ["#noSlop2", "#noSlopT"]) $(id).onclick = () => { setNoSlop(!NOSLOP); toast(NOSLOP ? "Claude and Codex will skip the overused stock sounds" : "AI slop audio filter off"); };
setNoSlop(NOSLOP);


// ---------------------------------------------------------------- Settings
async function openSettings() {
  const j = await api("/api/settings");
  $("#setRestricted").checked = j.use_restricted_assets;
  const ul = $("#setList"); ul.innerHTML = "";
  for (const [dir, why] of Object.entries(j.restricted)) {
    const li = document.createElement("li"); const b = document.createElement("b");
    b.textContent = dir.replace("assets/Default assets/", "").replace(/\/$/, ""); li.append(b, " - " + why); ul.appendChild(li);
  }
  $("#setModal").classList.remove("hidden");
}
$("#setBtn").onclick = openSettings;
$("#setClose").onclick = () => $("#setModal").classList.add("hidden");
$("#setRestricted").onchange = async () => {
  const j = await post("/api/settings", { use_restricted_assets: $("#setRestricted").checked });
  toast(j.use_restricted_assets ? "Claude and Codex may use every asset" : "Only shareable assets will be used");
  if (MODE === "editor") renderBin(); if (MODE === "make") renderMakeBin();
};

loadVideos();
