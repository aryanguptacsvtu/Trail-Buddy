"""Writes a self-contained, offline HTML page next to the markdown journal."""
import html

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{route} - TrailBuddy</title><style>
:root{{--bg:#efe9da;--card:#f8f4ea;--ink:#2a2a22;--mute:#6b6a5a;--moss:#3f5d3a;--rust:#b4532a;--line:#d6cfba}}
@media (prefers-color-scheme:dark){{:root{{--bg:#171a14;--card:#1f241b;--ink:#e8e4d4;--mute:#9a9a86;--moss:#8fb97f;--rust:#e0875a;--line:#343a2d}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.65 Cambria,'Palatino Linotype','Iowan Old Style','Source Serif 4',Georgia,serif;font-variant-numeric:lining-nums;padding:28px 16px}}
main{{max-width:640px;margin:0 auto}}
.kicker{{font:600 12px/1 ui-monospace,Consolas,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--moss)}}
h1{{font-size:clamp(30px,7vw,46px);line-height:1.1;margin:10px 0 4px;letter-spacing:-.01em}}
.date{{color:var(--mute);font-style:italic;margin:0 0 26px}}
.meter{{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:20px}}
.meter p{{margin:0 0 12px}}.meter b{{color:var(--rust);font-size:1.15em}}
.bar{{height:14px;background:var(--moss);border-radius:7px;position:relative;overflow:hidden}}
.bar i{{position:absolute;left:0;top:0;bottom:0;background:var(--rust);width:{pct}%;min-width:3px}}
.legend{{display:flex;justify-content:space-between;font:12px ui-monospace,Consolas,monospace;color:var(--mute);margin-top:8px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:18px 0 30px}}
.stats div{{border-top:2px solid var(--moss);padding-top:8px}}
.stats span{{display:block;font:11px ui-monospace,Consolas,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--mute)}}
.stats strong{{font-size:22px}}
.entry{{border-left:3px solid var(--moss);padding-left:18px;white-space:normal}}
footer{{margin-top:34px;font:12px ui-monospace,Consolas,monospace;color:var(--mute)}}
</style></head><body><main>
<div class="kicker">TrailBuddy field journal</div>
<h1>{route}</h1><p class="date">{date}</p>
<section class="meter"><p>Screen on for <b>{screen}</b> during a <b>{outing} min</b> outing.</p>
<div class="bar" role="img" aria-label="Screen time share of outing"><i></i></div>
<div class="legend"><span>screen {pct}%</span><span>eyes up {rest}%</span></div></section>
<div class="stats"><div><span>Unlocks</span><strong>{unlocks}</strong></div>
<div><span>Missions</span><strong>{missions}</strong></div>
<div><span>Route</span><strong>{km} km</strong></div></div>
<div class="entry">{text}</div>
<footer>Planned, narrated and written on-device with open-source models. Nothing left the laptop.</footer>
</main></body></html>"""

def write_html(path, route, text, stats):
    secs = stats["screen_s"]
    total = max(stats["outing_min"] * 60, 1)
    pct = round(min(secs / total * 100, 100), 1)
    page = PAGE.format(
        route=html.escape(route), date=html.escape(stats.get("date", "")),
        text=html.escape(text), screen=f"{secs // 60}m {secs % 60}s",
        outing=stats["outing_min"], pct=pct, rest=round(100 - pct, 1),
        unlocks=stats["unlocks"], missions=html.escape(str(stats["missions_done"])),
        km=stats.get("route_km", "-"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)