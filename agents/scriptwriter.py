"""Agent 3 - Scriptwriter: hook (first 3 s) + body + CTA, grounded in facts.json. Rules engine by default,
local LLM (Ollama, free) if LLM_PROVIDER=ollama. LLM output is validated; on any problem we fall back to rules."""
import re
from core import llm, config as C
from core.rag import tokenize

NUM = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}
CONNECT = ["First,", "Next,", "Also,", "And remember,", "Finally,"]
CTA_TAGS = {"helpline", "report", "portal", "contact"}


def _lower_first(s):
    return s[0].lower() + s[1:] if len(s) > 1 and s[1].islower() else s


def wc(t):
    return len(t.split())


def _rules(plan, brief, facts, fb):
    mx = fb.get("max_words") or plan["word_budget"]["max"]
    mn = min(fb.get("min_words") or plan["word_budget"]["min"], mx)
    avoid = set(fb.get("avoid_fact_ids", []))
    pool = [f for f in facts if f["id"] not in avoid]
    must = [str(m).lower() for m in brief.get("must_include", [])]
    cta = [f for f in pool if (set(f["tags"]) & CTA_TAGS)]
    cta_must = [f for f in cta if any(m in f["claim"].lower() for m in must)]
    cta_opt = [f for f in cta if f not in cta_must]
    body = [f for f in pool if f not in cta]
    sub = plan["subtopics"]
    hook_t = f"{sub[0].strip().capitalize()}. {{n}} things every student must know."
    # coverage: best body fact per sub-topic, then the rest by order
    chosen = []
    for s in sub:
        st = set(tokenize(s))
        best = max(body, key=lambda f: len(st & set(tokenize(f["claim"] + " " + " ".join(f["tags"])))), default=None)
        if best and st & set(tokenize(best["claim"] + " " + " ".join(best["tags"]))) and best not in chosen:
            chosen.append(best)
    extras = [f for f in body if f not in chosen]
    cta_lines = list(cta_must)

    def total(bd, ct):
        return wc(hook_t.format(n=NUM.get(len(bd), "Some"))) + sum(wc(f["claim"]) + 2 for f in bd) + sum(wc(f["claim"]) for f in ct)

    while chosen and total(chosen, cta_lines) > mx:      # too long: drop least-covering (last) body fact
        chosen.pop()
    for f in extras + cta_opt:                           # room left: add optional facts (body first)
        tgt = chosen if f in extras else cta_lines
        if total(chosen + ([f] if tgt is chosen else []), cta_lines + ([f] if tgt is cta_lines else [])) <= mx:
            tgt.append(f)
    chosen.sort(key=lambda f: f["id"])
    cta_lines.sort(key=lambda f: (f in cta_must, f["id"]))
    lines = [{"role": "hook", "text": hook_t.format(n=NUM.get(len(chosen), "Some")), "fact_ids": []}]
    for i, f in enumerate(chosen):
        c = CONNECT[min(i, len(CONNECT) - 1)] if i < len(chosen) - 1 or len(chosen) < 3 else CONNECT[3]
        lines.append({"role": "body", "text": f"{c} {_lower_first(f['claim'])}", "fact_ids": [f["id"]]})
    for f in cta_lines:
        lines.append({"role": "cta", "text": f["claim"], "fact_ids": [f["id"]]})
    return lines


def _llm(plan, brief, facts, fb):
    tpl = (C.ROOT / "prompts/script_v1.txt").read_text()
    sysm, user = tpl.split("USER:", 1)
    sysm = sysm.replace("SYSTEM:", "").strip()
    fmt = dict(tone=brief.get("tone", ""), audience=brief.get("audience", ""), min_words=plan["word_budget"]["min"],
               max_words=fb.get("max_words") or plan["word_budget"]["max"], cta=brief.get("cta", ""),
               must_avoid=", ".join(map(str, brief.get("must_avoid", []))), feedback="; ".join(fb.get("notes", [])) or "none",
               facts="\n".join(f"[{f['id']}] {f['claim']}" for f in facts))
    out, ti, to = llm.generate_json(user.format(**fmt), sysm.format(**{k: fmt[k] for k in ("tone", "audience")}))
    ids = {f["id"] for f in facts}
    lines = out["lines"]
    for l in lines:
        if not set(l.get("fact_ids", [])) <= ids or not l.get("text"):
            raise ValueError("LLM cited unknown fact id or empty text")
        l.setdefault("fact_ids", [])
    return lines, ti, to


def run(plan, brief, facts_doc, fb=None, logger=None):
    fb = fb or {}
    facts = facts_doc["facts"]
    method, ti, to = "rules", 0, 0
    lines = None
    if llm.available():
        try:
            lines, ti, to = _llm(plan, brief, facts, fb)
            method = "llm:" + llm.model_name()
        except Exception as e:
            if logger:
                logger.record("scriptwriter", "llm", llm.model_name(), "script_v1", status=f"fallback_to_rules: {e}"[:200])
    if lines is None:
        lines = _rules(plan, brief, facts, fb)
    for i, l in enumerate(lines):
        l["id"] = f"L{i + 1}"
        l["words"] = wc(l["text"])
    return {"method": method, "lines": lines, "word_count": sum(l["words"] for l in lines),
            "tokens": {"input": ti, "output": to}, "feedback_applied": fb}


def to_markdown(script, timings=None):
    out = ["# Script", f"_method: {script['method']} · {script['word_count']} words_", ""]
    for l in script["lines"]:
        ts = f"[{timings[l['id']][0]:05.2f}-{timings[l['id']][1]:05.2f}] " if timings and l["id"] in timings else ""
        out.append(f"- {ts}**{l['role'].upper()}** {l['text']}  _(facts: {', '.join(l['fact_ids']) or '—'})_")
    return "\n".join(out) + "\n"
