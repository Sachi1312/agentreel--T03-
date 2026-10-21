"""Agent 1 - Planner: brief.yaml -> plan.json (stages, time/cost budget split, queries, success criteria)."""
import re
from core import config as C


def split_topic(topic):
    parts = re.split(r"[:;,]| and |/", topic)
    return [p.strip() for p in parts if len(p.strip()) > 2]


def run(brief, live=False):
    dur = float(brief["duration_s"])
    fmt = brief.get("format", "video_9x16")
    if fmt not in C.FORMATS:
        raise ValueError(f"format '{fmt}' not supported by this pipeline (video_9x16 / video_16x9 only)")
    vo_seconds = dur - C.ENDCARD_S - 1.2
    words = int(vo_seconds * C.WORDS_PER_SEC)
    total_s = C.LIVE_RUN_SECONDS if live else 1800
    split = {"planner": .01, "researcher": .04, "scriptwriter": .10, "storyboarder": .05,
             "asset_generator": .30, "editor": .30, "critic": .05, "human_review": .15}
    stages = [{"agent": a, "time_budget_s": int(total_s * f), "cost_budget_inr": 0.0} for a, f in split.items()]
    sensitive = any(brief.get("category", "").startswith(c) for c in C.SENSITIVE_CATEGORIES)
    subtopics = split_topic(brief["topic"])
    queries = list(dict.fromkeys(subtopics + [str(m) for m in brief.get("must_include", [])] + ["how to report", "what should you do"]))
    plan = {
        "brief_id": brief["id"], "format": fmt, "duration_s": dur, "endcard_s": C.ENDCARD_S,
        "word_budget": {"min": int(words * 0.85), "max": words},
        "sensitive": sensitive, "subtopics": subtopics, "queries": queries,
        "stages": stages, "total_budget_inr": C.BUDGET_INR, "planned_spend_inr": 0.0,
        "max_critic_loops": C.MAX_LOOPS,
        "success_criteria": [
            f"duration {C.MIN_DUR}-{C.MAX_DUR}s (target {dur}s)", "every claim cites a fact id; numbers/URLs/phones exist in fact sheet",
            "hook names the topic in first 3 s", "burned-in captions >=48px inside safe zones + .srt",
            f"loudness {C.TARGET_LUFS}±{C.LUFS_TOL} LUFS, true peak <= {C.MAX_TRUE_PEAK} dBTP",
            "end card: logo + CTA + AI-disclosure line", "must_include present, must_avoid absent"]
            + (["mandatory human review before export"] if sensitive else []),
    }
    return plan
