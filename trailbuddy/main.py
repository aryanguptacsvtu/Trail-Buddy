import argparse, datetime, os, time
from . import llm, router


def main():

    ap = argparse.ArgumentParser()
    ap.add_argument("request", help='e.g. "2 hours, moderate fitness, scenic"')
    ap.add_argument("--max-min", type=int, help="time budget in minutes")
    ap.add_argument("--text", action="store_true", help="type instead of using mic/speakers")
    a = ap.parse_args()

    if a.text:
        speak, listen = (lambda t: print(f"TrailBuddy: {t}")), (lambda: input("you> "))
    else:
        from .voice import speak, listen

    cands = router.candidates(max_min=a.max_min)
    if not cands:
        raise SystemExit("Put some .gpx files in routes/ first.")
    
    p = llm.plan(a.request, cands)
    route = cands[p["chosen"]]
    plan_text = f"{route['name']}: {route['km']} km, {route['gain_m']} m climb, ~{route['est_min']} min. {p['why']}"
    missions, done = p["missions"], set()

    speak("Plan ready. " + plan_text)
    print("\nMissions:", *[f"  {i}. {m}" for i, m in enumerate(missions)], sep="\n")
    print("\nSafety:", *[f"  - {s}" for s in p["safety"]], sep="\n")
    print("\nLock your screen. Enter=talk, s=toggle screen-on, q=finish\n")

    start, log, history = time.time(), [], []
    screen_on_since, screen_secs, unlocks = None, 0.0, 0

    while True:
        cmd = input("> ").strip().lower()
        if cmd == "q":
            break
        if cmd == "s":
            if screen_on_since is None:
                screen_on_since, unlocks = time.time(), unlocks + 1
                print("  screen ON (counting)")
            else:
                screen_secs += time.time() - screen_on_since
                screen_on_since = None
                print("  screen OFF")
            continue
        said = listen()
        if not said:
            continue
        
        md = llm.classify(missions, done, said)
        
        if md is not None:
            done.add(md)
        
        r = llm.reply(plan_text, missions, done, history, said, md)
        history += [{"role": "user", "content": said}, {"role": "assistant", "content": r}]
        log.append({"min": round((time.time() - start) / 60, 1), "hiker_said": said,
                    "mission_completed": missions[md] if md is not None else None})
        speak(r)

    if screen_on_since:
        screen_secs += time.time() - screen_on_since

    total = time.time() - start
    stats = {"date": str(datetime.date.today()), "outing_min": round(total / 60),
             "screen_s": round(screen_secs), "unlocks": unlocks,
             "missions_done": f"{len(done)}/{len(missions)}", "route": route["name"],
             "route_km": route["km"]}
    
    text = llm.journal(log, stats)
    os.makedirs("journals", exist_ok=True)

    path = f"journals/{datetime.datetime.now():%Y-%m-%d_%H%M}-{route['name']}.md"
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {route['name']}\n\n{text}\n\n---\n"
                f"- Outing: {stats['outing_min']} min\n"
                f"- Screen time: {stats['screen_s'] // 60} min {stats['screen_s'] % 60} s ({unlocks} unlocks)\n"
                f"- Missions: {stats['missions_done']}\n")
    
    speak("Journal saved.")
    print("Saved", path)


if __name__ == "__main__":
    main()
