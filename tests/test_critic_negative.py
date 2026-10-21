"""The Critic must actually REJECT bad content (otherwise a pass means nothing).  python -m tests.test_critic_negative"""
import json, sys, tempfile
from pathlib import Path
from agents import critic
from core import config as C

OUT = sorted((C.ROOT / "outputs").glob("T00-A05-*"))[-1]
load = lambda n: json.loads((OUT / n).read_text())
plan, facts, script, sb = load("plan.json"), load("facts.json"), load("script.json"), load("storyboard.json")
import yaml
brief = yaml.safe_load((OUT / "brief.yaml").read_text())
edit = {"final": str(next(OUT.glob("*_final.mp4")))}
timings = {l["id"]: (0.3, 3.0) for l in script["lines"]}
assets = {"timings": timings}
srt = OUT / "captions.srt"


def failing(mutate):
    s, b = json.loads(json.dumps(script)), json.loads(json.dumps(brief))
    mutate(s, b)
    qa = critic.run(plan, b, facts, s, sb, assets, edit, OUT, srt)
    return {c["id"] for c in qa["checks"] if not c["passed"]}


tests = {
    "wrong helpline number": (lambda s, b: s["lines"][-2].update(text="The National Cyber Crime Helpline number is 1931."), "fact_grounding"),
    "invented website": (lambda s, b: s["lines"][-1].update(text="You can also report cybercrime online at cyberhelp.gov.in."), "contacts_verified"),
    "uncited claim": (lambda s, b: s["lines"][2].update(fact_ids=[]), "fact_grounding"),
    "made-up statistic": (lambda s, b: s["lines"][1].update(text="Over 90000 students lost money to digital arrest last year."), "fact_grounding"),
    "template text left in": (lambda s, b: s["lines"][3].update(text="<insert contact here>"), "no_placeholders"),
    "must_avoid word used": (lambda s, b: s["lines"][1].update(text=s["lines"][1]["text"] + " Show the victim's face."), "must_avoid"),
    "must_include removed": (lambda s, b: b.update(must_include=["Tele-MANAS 14416"]), "must_include"),
}
bad = 0
for name, (mut, expect) in tests.items():
    f = failing(mut)
    ok = expect in f
    bad += not ok
    print(("PASS" if ok else "FAIL"), f"{name}: critic flagged {sorted(f)}")
print("clean baseline:", sorted(failing(lambda s, b: None)) or "no failures")
sys.exit(1 if bad else 0)
