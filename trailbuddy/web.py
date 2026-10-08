"""Local web UI for TrailBuddy.

Standard library server + the existing llm / router / report modules, so there
are no new dependencies and the CLI (run.py) is unaffected.  Everything runs on
this machine: the browser talks to this server, this server talks to Ollama.

    python serve.py            # then open http://127.0.0.1:8765
"""
import argparse, base64, datetime, json, os, re, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

from . import llm, router
from .report import write_html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # project folder (routes/, journals/)
STATIC = os.path.join(HERE, "static")
INDEX = os.path.join(STATIC, "index.html")
STATIC_TYPES = {".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8"}
MAX_BODY = 12 * 1024 * 1024                       # photos are resized client-side, this is a safety cap


class ApiError(Exception):
    def __init__(self, msg, code=400):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------- API handlers
DEFAULT_REQUEST = "a scenic outdoor walk"        # the form is gone, so the planner gets a neutral brief


def _build(route, p):
    """Turn a raw llm.plan() result for one route into the API payload."""
    why = str(p.get("why", "")).strip()
    missions = [str(m) for m in (p.get("missions") or [])][:8]
    safety = [str(x) for x in (p.get("safety") or [])][:8]
    if not missions:
        raise ApiError("The model didn't return any missions. Please try again.", 502)
    plan_text = (f"{route['name']}: {route['km']} km, {route['gain_m']} m climb, "
                 f"~{route['est_min']} min. {why}")
    return {"route": route, "why": why, "missions": missions, "safety": safety,
            "plan_text": plan_text}


def api_trails(_d=None):
    """Every trail in routes/. No model call: this is just the list."""
    cands = router.candidates()
    if not cands:
        raise ApiError("Put some .gpx files in the routes/ folder first.")
    return {"routes": cands}


def api_route(d):
    """Missions + safety for the trail the person picked."""
    name = str(d.get("name") or "")
    route = next((c for c in router.candidates() if c["name"] == name), None)
    if not route:
        raise ApiError("That trail isn't in the routes/ folder.", 404)
    return _build(route, llm.plan(DEFAULT_REQUEST, [route]))


def api_chat(d):
    said = str(d.get("said") or "").strip()
    if not said:
        raise ApiError("Say or type something first.")
    missions = [str(m) for m in d.get("missions", [])]
    done = {i for i in d.get("done", []) if isinstance(i, int) and 0 <= i < len(missions)}
    history = [h for h in d.get("history", []) if isinstance(h, dict)
               and h.get("role") in ("user", "assistant") and isinstance(h.get("content"), str)]
    plan_text = str(d.get("plan_text") or "")
    try:
        md = llm.classify(missions, done, said)      # same mission detection as the CLI
    except Exception:
        md = None
    if md is not None:
        done.add(md)
    text = llm.reply(plan_text, missions, done, history, said, md)
    return {"reply": text, "mission": md}


def api_scan(d):
    img = str(d.get("image") or "")
    if "," in img:                                   # strip "data:image/jpeg;base64,"
        img = img.split(",", 1)[1]
    try:
        base64.b64decode(img, validate=True)
    except Exception:
        raise ApiError("That doesn't look like a valid image.")
    prompt = ("You are TrailBuddy, an outdoor companion. Look at this photo taken outside. "
              "In at most two short sentences say what it shows and, only if you are "
              "confident, one interesting fact. " + llm.SAFETY)
    body = {"model": llm.MODEL, "stream": False, "options": {"temperature": 0.3},
            "messages": [{"role": "user", "content": prompt, "images": [img]}]}
    r = requests.post(f"{llm.HOST}/api/chat", json=body, timeout=180)
    if r.status_code >= 400:
        raise ApiError(f"The model '{llm.MODEL}' couldn't read the photo. "
                       "Photo scanning needs a vision model such as gemma3:4b.", 502)
    return {"text": r.json()["message"]["content"].strip()}


def api_finish(d):
    route = d.get("route") or {}
    name = str(route.get("name") or "outing")
    stats_in = d.get("stats") or {}
    log = d.get("log") if isinstance(d.get("log"), list) else []
    stats = {"date": str(datetime.date.today()),
             "outing_min": int(stats_in.get("outing_min", 0)),
             "screen_s": int(stats_in.get("screen_s", 0)),
             "unlocks": int(stats_in.get("unlocks", 0)),
             "missions_done": str(stats_in.get("missions_done", "0/0")),
             "route": name, "route_km": route.get("km", "-")}
    text = " ".join(llm.journal(log, stats).split())
    os.makedirs("journals", exist_ok=True)
    safe = re.sub(r"[^\w\- ]", "", name).strip() or "outing"
    stamp = f"{datetime.datetime.now():%Y-%m-%d_%H%M}-{safe}"
    md_path, html_path = f"journals/{stamp}.md", f"journals/{stamp}.html"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {name}\n\n{text}\n\n---\n"
                f"- Outing: {stats['outing_min']} min\n"
                f"- Screen time: {stats['screen_s'] // 60} min {stats['screen_s'] % 60} s "
                f"({stats['unlocks']} unlocks)\n"
                f"- Missions: {stats['missions_done']}\n")
    write_html(html_path, name, text, stats)
    return {"text": text, "report_url": "/" + html_path, "saved": md_path}


def api_health(_d=None):
    try:
        r = requests.get(f"{llm.HOST}/api/tags", timeout=3)
        ok = r.ok
    except requests.RequestException:
        ok = False
    return {"ollama": ok, "model": llm.MODEL, "routes": len(router.candidates())}


POST = {"/api/trails": api_trails, "/api/route": api_route, "/api/chat": api_chat,
        "/api/scan": api_scan, "/api/finish": api_finish}


# ------------------------------------------------------------------- HTTP layer
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):                       # keep the terminal quiet
        pass

    def _send(self, code, body, ctype):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json; charset=utf-8")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            with open(INDEX, "r", encoding="utf-8") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if path.startswith("/static/"):              # style.css / app.js only; basename blocks ../
            name = os.path.basename(path)
            full = os.path.join(STATIC, name)
            ctype = STATIC_TYPES.get(os.path.splitext(name)[1])
            if ctype and os.path.isfile(full):
                with open(full, "r", encoding="utf-8") as f:
                    return self._send(200, f.read(), ctype)
        if path == "/api/health":
            return self._json(200, api_health())
        if path.startswith("/journals/"):            # saved reports only; basename blocks ../
            name = os.path.basename(path)
            full = os.path.join(ROOT, "journals", name)
            if name.endswith((".html", ".md")) and os.path.isfile(full):
                ctype = "text/html; charset=utf-8" if name.endswith(".html") else "text/plain; charset=utf-8"
                with open(full, "r", encoding="utf-8") as f:
                    return self._send(200, f.read(), ctype)
        self._json(404, {"error": "Not found"})

    def do_POST(self):
        fn = POST.get(self.path.split("?", 1)[0])
        if not fn:
            return self._json(404, {"error": "Not found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ApiError("Request too large.", 413)
            data = json.loads(self.rfile.read(n) or b"{}")
            self._json(200, fn(data))
        except ApiError as e:
            self._json(e.code, {"error": str(e)})
        except requests.ConnectionError:
            self._json(503, {"error": f"Can't reach Ollama at {llm.HOST}. "
                                      "Start it (ollama serve) and try again."})
        except requests.Timeout:
            self._json(504, {"error": "The local model took too long to answer."})
        except json.JSONDecodeError:
            self._json(502, {"error": "The model sent back something unreadable. Please try again."})
        except Exception as e:                       # never crash the server on one bad request
            self._json(500, {"error": f"{type(e).__name__}: {e}"})


def main(argv=None):
    ap = argparse.ArgumentParser(description="TrailBuddy local web UI")
    ap.add_argument("--host", default="127.0.0.1", help="default keeps it private to this machine")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args(argv)
    os.chdir(ROOT)                                   # routes/ and journals/ resolve like the CLI
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    url = f"http://{a.host}:{a.port}"
    print(f"TrailBuddy UI running at {url}  (Ctrl+C to stop)")
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nBye - go touch some grass.")


if __name__ == "__main__":
    main()