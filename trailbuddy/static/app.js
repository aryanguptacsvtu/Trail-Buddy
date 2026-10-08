"use strict";
const $ = id => document.getElementById(id);
const KEY = "trailbuddy.session.v1";
const fresh = () => ({
    route: null, plan_text: "", missions: [], safety: [], done: [], log: [], history: [],
    discoveries: 0, timer: { running: true, base: 0, since: Date.now() }, screen: { on: false, secs: 0, since: null, unlocks: 0 }
});
let S = null, pending = null, plans = {}, routeList = [], selName = "", pickTok = 0;

/* ---------- helpers ---------- */
function show(id) { for (const v of ["landing", "plan", "session", "done"]) $("v-" + v).hidden = v !== id; window.scrollTo(0, 0); }
function save() { try { if (S) sessionStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { } }
async function api(path, body) {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.error || "Request failed (" + r.status + ")");
    return j;
}
function err(el, msg) { el.textContent = msg; el.hidden = !msg; }
function fill(list, items) { list.replaceChildren(...items.map(t => { const li = document.createElement("li"); li.textContent = t; return li; })); }
const elapsed = () => S.timer.base + (S.timer.running ? (Date.now() - S.timer.since) / 1000 : 0);
const screenSecs = () => S.screen.secs + (S.screen.on ? (Date.now() - S.screen.since) / 1000 : 0);
const mins = () => Math.round(elapsed() / 6) / 10;
function fmt(s) {
    s = Math.floor(s); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = s % 60, p = n => String(n).padStart(2, "0");
    return h ? h + ":" + p(m) + ":" + p(x) : p(m) + ":" + p(x);
}

/* ---------- landing ---------- */
fetch("/api/health").then(r => r.json()).then(h => {
    const bits = [];
    bits.push(h.ollama ? "✅ Local model ready (" + h.model + ")" : "⚠️ Ollama not detected. Start it with: ollama serve");
    bits.push(h.routes ? "✅ " + h.routes + " trail" + (h.routes > 1 ? "s" : "") + " loaded" : "⚠️ No .gpx files found in routes/");
    $("health").innerHTML = ""; bits.forEach(b => { const d = document.createElement("div"); d.textContent = b; $("health").appendChild(d); });
}).catch(() => { });
$("startBtn").onclick = openPlan;
$("planBack").onclick = () => show("landing");

/* ---------- plan ---------- */
function showPlan(p) {
    pending = p; selName = p.route.name;
    const r = p.route;
    $("pRoute").textContent = r.name;
    $("pChips").replaceChildren(...[r.km + " km", r.gain_m + " m climb", "~" + r.est_min + " min"].map(t => { const c = document.createElement("span"); c.className = "chip"; c.textContent = t; return c; }));
    $("pWhy").textContent = p.why;
    fill($("pMissions"), p.missions); fill($("pSafety"), p.safety);
    $("planDetail").hidden = false; renderCards();
}
function renderCards() {
    $("routeCards").replaceChildren(...routeList.map(r => {
        const b = document.createElement("button");
        b.type = "button"; b.className = "rcard" + (r.name === selName ? " sel" : "");
        const n = document.createElement("b"); n.textContent = r.name;
        const m = document.createElement("span"); m.textContent = r.km + " km · " + r.gain_m + " m climb · ~" + r.est_min + " min";
        b.append(n, m);
        b.onclick = () => pick(r);
        return b;
    }));
}
async function pick(r) {
    if (r.name === selName) return;
    const tok = ++pickTok;
    err($("planErr"), "");
    if (plans[r.name]) { showPlan(plans[r.name]); $("routeState").textContent = ""; $("beginBtn").disabled = false; return; }
    const prev = selName; selName = r.name; $("planDetail").hidden = true; renderCards();
    $("beginBtn").disabled = true; $("routeState").textContent = "Writing missions for " + r.name + " with your local model…";
    try {
        const p = await api("/api/route", { name: r.name });
        if (tok !== pickTok) return;
        plans[r.name] = p; showPlan(p); $("planDetail").scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (e) {
        if (tok !== pickTok) return;
        err($("planErr"), e.message); selName = prev; $("planDetail").hidden = !prev; renderCards();
    }
    $("beginBtn").disabled = false; $("routeState").textContent = "";
}
async function openPlan() {                       // landing -> plan: just list the trails, no model call
    plans = {}; routeList = []; selName = ""; pending = null; ++pickTok;
    $("routeCards").replaceChildren(); $("planDetail").hidden = true; err($("planErr"), "");
    $("routeState").textContent = "Loading trails…"; show("plan");
    try { routeList = (await api("/api/trails", {})).routes; renderCards(); }
    catch (e) { err($("planErr"), e.message); }
    $("routeState").textContent = "";
}
$("beginBtn").onclick = () => {
    S = fresh();
    Object.assign(S, { route: pending.route, plan_text: pending.plan_text, missions: pending.missions, safety: pending.safety });
    save(); enterSession();
};

/* ---------- session ---------- */
function enterSession() {
    $("sRoute").textContent = S.route.name + " · " + S.route.km + " km · ~" + S.route.est_min + " min";
    fill($("allS"), S.safety);
    err($("sErr"), ""); show("session"); render();
}
function render() {
    const total = S.missions.length, left = S.missions.map((_, i) => i).filter(i => !S.done.includes(i));
    const cur = left[0];
    $("mNum").textContent = cur === undefined ? "ALL DONE" : "MISSION #" + String(cur + 1).padStart(2, "0");
    $("mText").textContent = cur === undefined ? "Every mission complete. 🎉" : S.missions[cur];
    $("mSub").textContent = cur === undefined ? "Enjoy the rest of your time outside, or end the session to get your journal." : "Look around you and notice it. Then tell TrailBuddy, or tap complete.";
    $("doneBtn").hidden = cur === undefined;
    $("mDots").replaceChildren(...S.missions.map((_, i) => { const d = document.createElement("i"); if (S.done.includes(i)) d.className = "on"; return d; }));
    fill($("allM"), S.missions.map((m, i) => (S.done.includes(i) ? "✓ " : "") + m));
    $("stM").textContent = S.done.length + "/" + total; $("stD").textContent = S.discoveries;
    $("pauseBtn").textContent = S.timer.running ? "Pause" : "Resume";
    $("screenBtn").textContent = "Screen: " + (S.screen.on ? "on" : "off");
    tick();
}
function tick() {
    if (!S || $("v-session").hidden) return;
    const e = elapsed(), sc = screenSecs();
    $("clock").textContent = fmt(e);
    $("screenInfo").textContent = "Screen on for " + fmt(sc) + " · " + S.screen.unlocks + " unlock" + (S.screen.unlocks === 1 ? "" : "s");
    const pts = Math.max(0, S.done.length * 10 + S.discoveries * 5 + Math.floor(e / 60) - Math.floor(sc / 60));
    $("score").textContent = pts;
    $("scoreMsg").textContent = pts < 10 ? "Warming up." : pts < 30 ? "Nice. You're officially touching grass." : pts < 60 ? "Now we're talking. Keep exploring." : "Absolute trail legend.";
}
setInterval(tick, 1000);

function logEntry(said, mission) {
    const e = { min: mins(), hiker_said: said };
    if (mission !== undefined && mission !== null) e.mission_completed = S.missions[mission];
    S.log.push(e);
}
function completeMission(i, said) {
    if (S.done.includes(i)) return;
    S.done.push(i); logEntry(said, i); save(); render();
}
$("doneBtn").onclick = () => {
    const cur = S.missions.findIndex((_, i) => !S.done.includes(i));
    if (cur >= 0) completeMission(cur, "I finished this mission.");
};
$("pauseBtn").onclick = () => {
    if (S.timer.running) { S.timer.base = elapsed(); S.timer.running = false; }
    else { S.timer.since = Date.now(); S.timer.running = true; }
    save(); render();
};
$("resetBtn").onclick = () => { S.timer = { running: true, base: 0, since: Date.now() }; save(); render(); };
$("screenBtn").onclick = () => {
    if (S.screen.on) { S.screen.secs = screenSecs(); S.screen.on = false; S.screen.since = null; }
    else { S.screen.on = true; S.screen.since = Date.now(); S.screen.unlocks++; }
    save(); render();
};

/* location (browser only) */
$("locBtn").onclick = () => {
    if (!navigator.geolocation) { $("locTxt").textContent = "Location isn't available in this browser."; return; }
    $("locTxt").textContent = "Finding you…";
    navigator.geolocation.getCurrentPosition(
        p => { $("locTxt").textContent = p.coords.latitude.toFixed(5) + ", " + p.coords.longitude.toFixed(5) + " (±" + Math.round(p.coords.accuracy) + " m)"; },
        e => { $("locTxt").textContent = e.code === 1 ? "Permission denied. You can allow it in your browser's site settings." : "Couldn't get your location."; },
        { enableHighAccuracy: true, timeout: 15000 });
};

/* photo scanner */
function toJpeg(file, max) {
    return new Promise((res, rej) => {
        const img = new Image(), url = URL.createObjectURL(file);
        img.onload = () => {
            const k = Math.min(1, max / Math.max(img.width, img.height)), c = document.createElement("canvas");
            c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
            c.getContext("2d").drawImage(img, 0, 0, c.width, c.height); URL.revokeObjectURL(url); res(c.toDataURL("image/jpeg", .8));
        };
        img.onerror = () => rej(new Error("Couldn't read that image."));
        img.src = url;
    });
}
$("photoBtn").onclick = () => $("photoIn").click();
$("photoIn").onchange = async ev => {
    const f = ev.target.files[0]; ev.target.value = ""; if (!f) return;
    err($("sErr"), ""); $("scanOut").hidden = false; $("scanOut").textContent = "Looking closely…"; $("photoBtn").disabled = true;
    try {
        const data = await toJpeg(f, 768);
        const im = document.createElement("img"); im.src = data;
        $("dropBody").replaceChildren(im);
        const j = await api("/api/scan", { image: data });
        $("scanOut").textContent = j.text;
        S.discoveries++; logEntry("I photographed something: " + j.text); save(); render();
    } catch (e) { $("scanOut").hidden = true; err($("sErr"), e.message); }
    $("photoBtn").disabled = false;
};

/* chat */
function bubble(cls, text) { const d = document.createElement("div"); d.className = "msg " + cls; d.textContent = text; $("chat").appendChild(d); $("chat").scrollTop = 1e9; return d; }
async function send() {
    const said = $("said").value.trim(); if (!said) return;
    $("said").value = ""; $("sendBtn").disabled = true; err($("sErr"), "");
    bubble("u", said); const wait = bubble("b", "…");
    try {
        const j = await api("/api/chat", { said, plan_text: S.plan_text, missions: S.missions, done: S.done, history: S.history });
        wait.textContent = j.reply;
        S.history.push({ role: "user", content: said }, { role: "assistant", content: j.reply });
        if (j.mission !== null && j.mission !== undefined) {
            if (!S.done.includes(j.mission)) S.done.push(j.mission);
            bubble("sys", "✓ Mission complete: " + S.missions[j.mission]);
        }
        if (j.mission !== null || !said.includes("?")) logEntry(said, j.mission);  // same journal rule as the CLI
        save(); render();
    } catch (e) { wait.remove(); err($("sErr"), e.message); }
    $("sendBtn").disabled = false; $("said").focus();
}
$("sendBtn").onclick = send;
$("said").onkeydown = e => { if (e.key === "Enter") send(); };

/* ---------- finish ---------- */
async function finish() {
    if (S.screen.on) { S.screen.secs = screenSecs(); S.screen.on = false; S.screen.since = null; }
    const stats = {
        outing_min: Math.round(elapsed() / 60), screen_s: Math.round(S.screen.secs), unlocks: S.screen.unlocks,
        missions_done: S.done.length + "/" + S.missions.length
    };
    show("done"); $("dLoad").hidden = false; $("dBody").hidden = true; $("dRetry").hidden = true; err($("dErr"), "");
    try {
        const j = await api("/api/finish", { route: S.route, log: S.log, stats });
        $("dTiles").replaceChildren(...[[stats.outing_min + " min", "Outside"], [Math.floor(stats.screen_s / 60) + "m " + stats.screen_s % 60 + "s", "Screen time"], [stats.missions_done, "Missions"], [S.discoveries, "Discoveries"]]
            .map(([b, s]) => { const t = document.createElement("div"); t.className = "tile"; const bb = document.createElement("b"); bb.textContent = b; const sp = document.createElement("span"); sp.textContent = s; t.append(bb, sp); return t; }));
        $("dText").textContent = j.text; $("dLink").href = j.report_url;
        $("dLoad").hidden = true; $("dBody").hidden = false;
        try { sessionStorage.removeItem(KEY); } catch (e) { }
    } catch (e) { $("dLoad").hidden = true; err($("dErr"), e.message); $("dRetry").hidden = false; }
}
$("endBtn").onclick = () => { if (confirm("End this outing and write your journal?")) finish(); };
$("retryBtn").onclick = finish;
$("backBtn").onclick = () => enterSession();
$("newBtn").onclick = () => { S = null; $("chat").replaceChildren(); bubble("sys", "Ask a question, or tell me what you spotted. I'll tick off missions for you."); $("dropBody").innerHTML = '<div class="ico">📷</div><div>Photograph something interesting.</div>'; $("scanOut").hidden = true; openPlan(); };

/* resume after a refresh */
try { const raw = sessionStorage.getItem(KEY); if (raw) { S = JSON.parse(raw); if (S && S.route) enterSession(); else S = null; } } catch (e) { S = null; }