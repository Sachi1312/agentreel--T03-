#!/usr/bin/env python3
"""Append one human intervention to logs/interventions.md.  Usage: python tools/log_intervention.py STAGE "what changed" "why"
Editing a generated file by hand = 1 intervention (max 5 in the Live Run)."""
import sys, time
from pathlib import Path
if len(sys.argv) != 4:
    sys.exit(__doc__)
p = Path(__file__).resolve().parent.parent / "logs" / "interventions.md"
if not p.exists():
    p.write_text("# Human interventions (max 5 during the Live Run)\n\n| time | stage | what was changed | why |\n|---|---|---|---|\n")
with open(p, "a") as f:
    f.write(f"| {time.strftime('%H:%M:%S')} | {sys.argv[1]} | {sys.argv[2]} | {sys.argv[3]} |\n")
n = sum(1 for l in p.read_text().splitlines() if l.startswith("| ") and l[2].isdigit())
print(f"logged. interventions so far: {n}/5")
