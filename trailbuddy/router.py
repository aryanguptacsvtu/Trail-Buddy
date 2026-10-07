"""Loads real trails from GPX files (export them from OSM-based tools while online).
The LLM never invents routes; it only chooses between these."""
import glob, math, os
import xml.etree.ElementTree as ET


def _hav(a, b):
    r = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
   
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
   
    return 2 * r * math.asin(math.sqrt(h))


def load(path):
    root = ET.parse(path).getroot()
    pts = []
    
    for p in root.iter():
        if p.tag.endswith("trkpt"):
            ele = next((c.text for c in p if c.tag.endswith("ele")), "0")
            pts.append((float(p.get("lat")), float(p.get("lon")), float(ele)))
    
    km = sum(_hav(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    gain, last = 0.0, pts[0][2]
    
    for _, _, e in pts[1:]:          # 3 m threshold filters GPS elevation noise
        if e - last >= 3:
            gain += e - last
            last = e
        elif last - e >= 3:
            last = e
            
    minutes = km / 4.0 * 60 + gain / 10  # walking pace + 1 min per 10 m climbed
    
    return {"name": os.path.splitext(os.path.basename(path))[0],
            "km": round(km, 1), "gain_m": round(gain), "est_min": round(minutes)}


def candidates(folder="routes", max_min=None):
    
    out = [load(f) for f in sorted(glob.glob(os.path.join(folder, "*.gpx")))]
    if max_min:
        out = [c for c in out if c["est_min"] <= max_min * 1.15] or out
    
    return out
