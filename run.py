#!/usr/bin/env python3
"""One-command entry point:  python run.py --brief briefs/A05_practice.yaml --seed 42
Brief -> Planner -> Researcher -> Scriptwriter -> Storyboarder -> Asset Generator -> Editor -> Critic
      -> (fail: route back to the responsible agent, max 3 loops | pass: human review (A/C) -> export + logs)"""
import argparse, json, random, shutil, sys, time
from pathlib import Path
import numpy as np, yaml
from core import config as C, schemas
from core.logger import RunLogger
from core import llm
from agents import planner, researcher, scriptwriter, storyboarder, asset_generator, editor, critic, human_review

ORDER = ["planner", "researcher", "scriptwriter", "storyboarder", "asset_generator", "editor", "critic"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--team", default=C.env("TEAM_ID", "T00"))
    ap.add_argument("--live", action="store_true", help="Live Run mode (3 h budget in plan; review cannot be auto-approved)")
    ap.add_argument("--auto-approve-review", action="store_true", help="REHEARSAL ONLY: skip the interactive human review")
    ap.add_argument("--run-no", type=int, default=None)
    a = ap.parse_args()
    if a.live and a.auto_approve_review:
        sys.exit("--auto-approve-review is not allowed with --live")
    random.seed(a.seed); np.random.seed(a.seed)
    brief = yaml.safe_load(Path(a.brief).read_text())
    prior = len(list((C.ROOT / "outputs").glob(f"{a.team}-{brief['id']}-*"))) if (C.ROOT / "outputs").exists() else 0
    run_id = f"{a.team}-{brief['id']}-{a.run_no or prior + 1:02d}"
    out = C.ROOT / "outputs" / run_id
    out.mkdir(parents=True, exist_ok=True)
    log = RunLogger(C.ROOT, run_id)
    shutil.copy(a.brief, out / "brief.yaml")
    t_start = time.time()
    print(f"[{run_id}] start · llm={llm.provider()} · seed={a.seed}")
    if brief.get("format") == "digital_experience":
        sys.exit("digital_experience briefs are not implemented in this pipeline (video track only)")

    S, fb, loops, qa_hist = {}, {}, 0, []
    i = 0
    while True:
        for stage in ORDER[i:]:
            if stage == "planner":
                S["plan"] = log.call("planner", "rules", "rule-engine-v1", lambda: planner.run(brief, a.live), output_path=out / "plan.json", prompt_id="plan_v1")
                schemas.validate_plan(S["plan"]); (out / "plan.json").write_text(json.dumps(S["plan"], indent=2))
            elif stage == "researcher":
                S["facts"] = log.call("researcher", "rag-bm25", "bm25", lambda: researcher.run(S["plan"], brief), output_path=out / "facts.json", prompt_id="rag_v1")
                schemas.validate_facts(S["facts"]); (out / "facts.json").write_text(json.dumps(S["facts"], indent=2))
                for g in S["facts"]["gaps"]:
                    print("  ! research gap:", g)
            elif stage == "scriptwriter":
                S["script"] = log.call("scriptwriter", "llm" if llm.available() else "rules", llm.model_name(),
                                       lambda: scriptwriter.run(S["plan"], brief, S["facts"], fb.get("scriptwriter"), log), prompt_id="script_v1")
                schemas.validate_script(S["script"])
                (out / "script.json").write_text(json.dumps(S["script"], indent=2)); (out / "script.md").write_text(scriptwriter.to_markdown(S["script"]))
            elif stage == "storyboarder":
                S["sb"] = log.call("storyboarder", "rules", "rule-engine-v1", lambda: storyboarder.run(S["plan"], brief, S["script"], S["facts"]), output_path=out / "storyboard.json", prompt_id="storyboard_v1")
                schemas.validate_storyboard(S["sb"])
            elif stage == "asset_generator":
                S["assets"] = asset_generator.run(S["plan"], brief, S["script"], S["sb"], out, a.seed, log)
                (out / "storyboard.json").write_text(json.dumps(S["sb"], indent=2))
                (out / "script.md").write_text(scriptwriter.to_markdown(S["script"], S["assets"]["timings"]))
            elif stage == "editor":
                S["edit"] = log.call("editor", "pipeline", "ffmpeg", lambda: editor.run(S["plan"], brief, S["sb"], S["assets"], out, a.seed, a.team, fb.get("editor"), log),
                                     output_path=lambda: out / f"{a.team}_{brief['id']}_final.mp4", prompt_id="edit_v1")
            elif stage == "critic":
                S["qa"] = log.call("critic", "rules", "rule-engine-v1", lambda: critic.run(S["plan"], brief, S["facts"], S["script"], S["sb"], S["assets"], S["edit"], out, out / "captions.srt"),
                                   prompt_id="qa_v1")
                S["qa"]["loop"] = loops
                (out / "qa_report.json").write_text(json.dumps(S["qa"], indent=2, ensure_ascii=False))
                qa_hist.append(S["qa"])
            print(f"  ✓ {stage}")
        qa = S["qa"]
        for c in qa["checks"]:
            print(f"    [{'PASS' if c['passed'] else 'FAIL'}] {c['id']}: {c['detail']}")
        if qa["passed"]:
            break
        loops += 1
        (out / f"qa_report_loop{loops - 1}.json").write_text(json.dumps(qa, indent=2, ensure_ascii=False))
        if loops > C.MAX_LOOPS:
            print(f"!! QA still failing after {C.MAX_LOOPS} repair loops; exporting best effort with failing report.")
            break
        fails = [c for c in qa["checks"] if not c["passed"]]
        i = min(ORDER.index(c["owner"]) for c in fails)
        fb = {}
        for c in fails:
            f = fb.setdefault(c["owner"], {"notes": []})
            f["notes"].append(f"{c['id']}: {c['detail']}")
            for k in ("max_words", "min_words", "avoid_fact_ids", "lufs_offset"):
                if c.get(k):
                    f[k] = c[k]
        print(f"  ↺ loop {loops}: routing back to '{ORDER[i]}' because of {[c['id'] for c in fails]}")
        log.record("critic", "route_back", "rule-engine-v1", note=f"loop {loops} -> {ORDER[i]}: {[c['id'] for c in fails]}")

    # ---- human review checkpoint (Category A / C) -------------------------------------------------
    approved = True
    final = Path(S["edit"]["final"])
    if S["plan"]["sensitive"] and qa["passed"]:
        approved = human_review.run(S["plan"], S["script"], qa, final, out, log, a.auto_approve_review)
    # ---- export ------------------------------------------------------------------------------------
    exp = C.ROOT / "outputs"
    if approved:
        shutil.copy(final, exp / final.name)
        shutil.copy(out / "captions.srt", exp / final.name.replace("_final.mp4", "_final.srt"))
        shutil.copy(out / "qa_report.json", exp / "qa_report.json")
        shutil.copy(out / "script.md", exp / "script.md")
        shutil.copy(out / "facts.json", exp / "facts.json")
        shutil.copy(out / "plan.json", exp / "plan.json")
        shutil.copy(out / "storyboard.json", exp / "storyboard.json")
    for wv in (out / "assets").glob("*.wav"):   # large intermediates (re-creatable with the same command + seed)
        wv.unlink()
    wall = time.time() - t_start
    cost = sum(float(r["cost_inr"]) for r in map(json.loads, (C.ROOT / "logs/run_log.jsonl").read_text().splitlines()) if r["run_id"] == run_id)
    summ = {"run_id": run_id, "passed_qa": qa["passed"], "approved": approved, "loops": loops, "wall_time_s": round(wall, 1),
            "total_cost_inr": round(cost, 2), "human_interventions_counted": log.n_interventions, "measured": qa["measured"],
            "llm": llm.model_name(), "tts": S["assets"]["tts_provider"], "seed": a.seed}
    (out / "run_summary.json").write_text(json.dumps(summ, indent=2))
    print(json.dumps(summ, indent=2))
    sys.exit(0 if qa["passed"] and approved else 2)


if __name__ == "__main__":
    main()
