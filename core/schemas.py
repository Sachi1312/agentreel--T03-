"""Minimal JSON-schema-style validators (no external deps). Raise ValueError on bad structure."""


def _need(d, keys, where):
    if not isinstance(d, dict):
        raise ValueError(f"{where}: expected object")
    for k in keys:
        if k not in d:
            raise ValueError(f"{where}: missing '{k}'")


def validate_plan(p):
    _need(p, ["brief_id", "stages", "word_budget", "queries", "success_criteria"], "plan")
    for s in p["stages"]:
        _need(s, ["agent", "time_budget_s", "cost_budget_inr"], "plan.stage")


def validate_facts(f):
    _need(f, ["facts", "gaps"], "facts")
    for x in f["facts"]:
        _need(x, ["id", "claim", "source"], "facts.fact")


def validate_script(s):
    _need(s, ["lines", "word_count"], "script")
    if not s["lines"]:
        raise ValueError("script: no lines")
    for l in s["lines"]:
        _need(l, ["role", "text", "fact_ids"], "script.line")
        if not l["text"].strip():
            raise ValueError("script: empty line")


def validate_storyboard(sb):
    _need(sb, ["shots"], "storyboard")
    n = len(sb["shots"])
    if not 6 <= n <= 12:
        raise ValueError(f"storyboard: {n} shots, need 6-12 (incl. end card)")
    for s in sb["shots"]:
        _need(s, ["id", "visual", "on_screen_text", "duration_s", "asset_source"], "storyboard.shot")
