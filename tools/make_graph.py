#!/usr/bin/env python3
"""Draw docs/agent_graph.png (architecture diagram)."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parent.parent
fig, ax = plt.subplots(figsize=(14, 6.4)); ax.set_xlim(0, 14); ax.set_ylim(0, 6.4); ax.axis("off")
NAVY, TEAL, AMBER, RED, GREY = "#0B1E3F", "#2EC4B6", "#FFB703", "#E85D75", "#8A97B1"


def box(x, y, w, h, title, sub, fc=NAVY, tc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec="none"))
    ax.text(x + w / 2, y + h * 0.64, title, ha="center", va="center", color=tc, fontsize=10.5, fontweight="bold")
    ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center", color=tc, fontsize=7.6, alpha=.9)


def arrow(p, q, c=NAVY, style="-|>", ls="-", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=14, color=c, lw=1.6, ls=ls, connectionstyle=f"arc3,rad={rad}"))


box(0.2, 4.7, 1.9, 1.0, "brief.yaml", "topic · audience · format", fc=AMBER, tc=NAVY)
box(0.2, 2.9, 1.9, 1.0, "data/", "fact sheet · PDFs · logo", fc=AMBER, tc=NAVY)
xs = [2.6, 4.45, 6.3, 8.15, 10.0, 11.85]
names = [("1 Planner", "plan.json\nbudget + criteria"), ("2 Researcher", "RAG (TF-IDF)\nfacts.json + sources"),
         ("3 Scriptwriter", "hook · body · CTA\nscript.json"), ("4 Storyboarder", "6-12 shots\nstoryboard.json"),
         ("5 Asset Gen.", "Kokoro TTS · music\nmanifest.csv"), ("6 Editor", "Pillow + ffmpeg\nfinal.mp4 · .srt")]
for x, (t, s) in zip(xs, names):
    box(x, 4.7, 1.65, 1.0, t, s)
for a, b in zip(xs[:-1], xs[1:]):
    arrow((a + 1.65, 5.2), (b, 5.2))
arrow((2.1, 5.2), (2.6, 5.2), AMBER)
arrow((2.1, 3.4), (5.1, 4.7), AMBER, rad=-0.15)
box(5.6, 2.2, 3.4, 1.15, "7 Critic / QA", "16 explicit checks: duration · specs · loudness ·\nclaims vs facts · contacts · safe zones · disclosure", fc=TEAL, tc=NAVY)
arrow((12.7, 4.7), (9.0, 3.1), NAVY, rad=-0.1)
box(10.2, 2.2, 3.4, 1.15, "Human review checkpoint", "mandatory for Category A / C\n(not counted in the 5 interventions)", fc=RED, tc="white")
arrow((9.0, 2.78), (10.2, 2.78), TEAL)
ax.text(9.6, 3.0, "pass", ha="center", fontsize=8, color=NAVY)
arrow((6.4, 3.35), (7.1, 4.7), RED, ls="--", rad=-0.1)
ax.text(5.0, 4.05, "FAIL: route back to the responsible\nagent (script / storyboard / editor), max 3 loops", fontsize=8, color=RED, ha="center")
box(10.2, 0.5, 3.4, 1.0, "Export", "TeamID_BriefID_final.mp4 · .srt · qa_report.json", fc="#1d6f6a")
arrow((11.9, 2.2), (11.9, 1.5), NAVY)
box(0.2, 0.5, 9.0, 1.0, "Logging wrapper around EVERY model / tool call", "logs/run_log.jsonl (one line per call) · cost_report.csv · interventions.md · output SHA-256 · Rs cost (cap Rs 500)", fc="#33415f")
ax.text(0.2, 6.15, "Somaiya AgentReel — multi-agent pipeline (python run.py --brief briefs/A05.yaml --seed 42)", fontsize=12.5, fontweight="bold", color=NAVY)
fig.savefig(ROOT / "docs" / "agent_graph.png", dpi=170, bbox_inches="tight", facecolor="white")
print("saved docs/agent_graph.png")
