"""Mandatory human review checkpoint for Category A (Safety) and C (Responsible AI) briefs.
Does NOT count toward the 5-intervention limit (per handout 7.2)."""
import sys
from pathlib import Path


def run(plan, script, qa, final, outdir, logger, auto=False):
    summary = ["=" * 70, "HUMAN REVIEW CHECKPOINT (safe-messaging / verified-contacts / no-victim-portrayal)", "=" * 70,
               f"Video: {final}", "", "Script:"] + [f"  [{l['role']}] {l['text']}" for l in script["lines"]] + \
              ["", "QA: " + ("PASS" if qa["passed"] else "FAIL") + f" ({sum(c['passed'] for c in qa['checks'])}/{len(qa['checks'])} checks)",
               "Check manually: helpline/contacts correct, tone supportive, no fear imagery, no group blamed, legal wording as in documents."]
    (Path(outdir) / "review_request.md").write_text("\n".join(summary))
    print("\n".join(summary))
    if auto:
        logger.add_intervention("human_review", "AUTO-APPROVED via --auto-approve-review (DRY-RUN ONLY, not allowed for the Live Run)", "mandatory checkpoint bypassed for rehearsal", counted=False)
        return True
    if not sys.stdin.isatty():
        print("\nNo interactive terminal: review the video and re-run with --auto-approve-review after YOU have checked it.")
        return False
    ans = input("\nApprove for export? [y/N] ").strip().lower() == "y"
    logger.add_intervention("human_review", "approved" if ans else "REJECTED", "mandatory checkpoint", counted=False)
    return ans
