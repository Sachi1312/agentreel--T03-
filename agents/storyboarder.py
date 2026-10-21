"""Agent 4 - Storyboarder: script lines -> 6-12 shots (visual, on-screen text, duration, asset source)."""
from core import config as C

TAG_VISUAL = {"scam": "phone_warning", "upi": "rupee_lock", "job": "briefcase", "sextortion": "chat_shield",
              "helpline": "big_text", "portal": "portal"}
DESCR = {"phone_call": "illustrated phone receiving an unknown call", "phone_warning": "phone showing a caution triangle",
         "rupee_lock": "rupee coin with shield and padlock", "briefcase": "briefcase with a crossed-out fee tag",
         "chat_shield": "chat bubbles protected by a shield", "big_text": "ring badge with the helpline number",
         "portal": "browser window with the reporting portal", "shield": "teal shield with a check mark"}


def run(plan, brief, script, facts_doc):
    fmap = {f["id"]: f for f in facts_doc["facts"]}
    shots = []
    for l in script["lines"]:
        f = fmap.get(l["fact_ids"][0]) if l["fact_ids"] else None
        if l["role"] == "hook":
            visual, text = "shield", plan["subtopics"][0].strip().capitalize()
        else:
            visual = (f or {}).get("visual") or next((TAG_VISUAL[t] for t in (f or {}).get("tags", []) if t in TAG_VISUAL), "shield")
            text = (f or {}).get("headline") or " ".join(l["text"].split()[:5])
        shots.append({"id": f"S{len(shots) + 1}", "script_line": l["id"], "visual": visual, "on_screen_text": text,
                      "description": DESCR.get(visual.split(":")[0], "illustration"), "fact_ids": l["fact_ids"],
                      "duration_s": round(max(l["words"] / C.WORDS_PER_SEC + 0.6, 2.5), 2),
                      "asset_source": "generated: procedural illustration (original)"})
    if len(shots) > 11:   # merge trailing CTA shots so that 11 + end card <= 12
        shots = shots[:11]
    shots.append({"id": f"S{len(shots) + 1}", "script_line": None, "visual": "endcard", "on_screen_text": brief["cta"],
                  "description": "logo, call to action, AI-disclosure line", "fact_ids": [], "duration_s": plan["endcard_s"],
                  "asset_source": "official: logo (assets/logo.png) + generated text"})
    return {"format": plan["format"], "shots": shots}
