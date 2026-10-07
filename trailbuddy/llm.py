import json, os, requests

HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("TB_MODEL", "gemma3:4b")

def chat(messages, as_json=False):
    body = {"model": MODEL, "messages": messages, "stream": False,
            "options": {"temperature": 0.4}}
    
    if as_json:
        body["format"] = "json"
    r = requests.post(f"{HOST}/api/chat", json=body, timeout=180)
    r.raise_for_status()
    text = r.json()["message"]["content"]

    return json.loads(text) if as_json else text.strip()


SAFETY = ("Never identify mushrooms or give foraging advice. If unsure about any "
          "plant or animal, say you are not sure. Never claim to be the user's navigation.")


def plan(request, cands):

    prompt = (f"Hiker request: {request}\nCandidate routes (real, do not invent others):\n"
              f"{json.dumps(cands)}\n\nChoose the best one. Reply JSON: "
              '{"chosen": <index>, "why": "<one sentence>", '
              '"missions": ["<5 short outdoor observation missions, no screen needed>"], '
              '"safety": ["<4 short checklist items>"]}. ' + SAFETY)
    
    p = chat([{"role": "user", "content": prompt}], as_json=True)

    if not isinstance(p.get("chosen"), int) or not 0 <= p["chosen"] < len(cands):
        p["chosen"] = 0
    for i, c in enumerate(cands):          # trust the route name in the explanation over the index
        if c["name"] in p.get("why", ""):
            p["chosen"] = i

    return p


def classify(missions, done, said):

    if "?" in said or said.lower().split()[0] in {"how", "what", "which", "where", "when", "are", "is", "can", "do"}:
        return None  # questions are never mission reports
    open_ = {i: m for i, m in enumerate(missions) if i not in done}

    if not open_:
        return None
    
    prompt = (f"Open missions: {json.dumps(open_)}\nThe hiker said: \"{said}\"\n"
              'Did the hiker report completing one of these missions? Reply JSON: '
              '{"mission": <index number, or -1 if none>}. '
              "Only match if the hiker explicitly says they did or observed that exact thing. "
              "Mentioning a related word (like 'tree') is NOT enough.")
    
    m = chat([{"role": "user", "content": prompt}], as_json=True).get("mission")

    return m if isinstance(m, int) and m in open_ else None


def reply(plan_text, missions, done, history, said, just_done=None):

    left = [m for i, m in enumerate(missions) if i not in done]
    extra = (f"The hiker just completed: {missions[just_done]}. Acknowledge it in a few words "
             "and suggest one remaining mission. " if just_done is not None else "")
    
    sys = (f"You are TrailBuddy, a voice companion on a hike. Plan: {plan_text}\n"
           f"Missions left: {json.dumps(left)}\n{extra}"
           "Answer in at most two short spoken sentences, no markdown, no filler praise. " + SAFETY)
    msgs = [{"role": "system", "content": sys}] + history[-6:] + [{"role": "user", "content": said}]
    
    return chat(msgs)


def journal(log, stats):

    prompt = ("Write a short trail journal (about 120 words), first person, past tense, "
              "from this event log. Output ONLY the journal text: no title, no preamble, "
              "no closing question, no markdown. Use ONLY facts in the log and stats. "
              "Do not invent dates, times, distances, sightings or events. "
              "route_km is the planned route length, not distance walked. "
              "There is exactly one hiker; write as 'I'. Never mention another hiker."
              "If the log is short or empty, say so honestly in one or two sentences.\n"
              f"Log: {json.dumps(log)}\nStats: {json.dumps(stats)}")
    
    return chat([{"role": "user", "content": prompt}])
