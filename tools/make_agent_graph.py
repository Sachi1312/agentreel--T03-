"""Draws docs/agent_graph.png.  python -m tools.make_agent_graph"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from core import config as C

nodes = [("brief.yaml", "topic · audience\nformat · tone", 0.5), ("Planner", "plan.json\ntime + cost split", 2.6), ("Researcher\n(RAG / BM25)", "facts.json\nsource + page", 4.8),
         ("Scriptwriter", "script.md\nhook · body · CTA", 7.0), ("Storyboarder", "storyboard.json\n6-12 shots", 9.2),
         ("Asset Generator", "voice · music\ncaptions · manifest", 11.4), ("Editor", "ffmpeg: captions · logo\nend card · loudnorm", 13.6), ("Critic / QA", "qa_report.json\n17+ checkable rules", 15.8)]
fig, ax = plt.subplots(figsize=(19, 6.2)); ax.set_xlim(-0.6, 18.6); ax.set_ylim(-3.4, 3.4); ax.axis("off")
for i, (n, sub, x) in enumerate(nodes):
    c = "#123c69" if i not in (0,) else "#555"
    ax.add_patch(FancyBboxPatch((x - 0.95, 0.3), 1.9, 1.5, boxstyle="round,pad=0.05", fc=c, ec="#2ec4b6", lw=2))
    ax.text(x, 1.3, n, ha="center", va="center", color="white", fontsize=11, weight="bold")
    ax.text(x, 0.7, sub, ha="center", va="center", color="#bfe3ff", fontsize=8)
    if i:
        ax.add_patch(FancyArrowPatch((nodes[i - 1][2] + 0.97, 1.05), (x - 0.97, 1.05), arrowstyle="-|>", mutation_scale=16, color="#333", lw=1.6))
ax.add_patch(FancyArrowPatch((15.8, 0.25), (7.0, 0.25), connectionstyle="arc3,rad=-0.2", arrowstyle="-|>", mutation_scale=16, color="#d62828", lw=1.8, ls="--"))
ax.text(11.4, -1.9, f"FAIL → route back to the responsible agent (max {C.MAX_LOOPS} loops)\nscriptwriter: facts / contacts / duration · editor: format / loudness / safe zones", ha="center", color="#d62828", fontsize=10)
ax.add_patch(FancyBboxPatch((17.0, 0.3), 1.5, 1.5, boxstyle="round,pad=0.05", fc="#2ec4b6", ec="#123c69", lw=2))
ax.text(17.75, 1.05, "Human review\n(Cat. A / C)\n→ export", ha="center", va="center", fontsize=9, weight="bold", color="#0b1830")
ax.add_patch(FancyArrowPatch((16.77, 1.05), (17.0, 1.05), arrowstyle="-|>", mutation_scale=14, color="#333", lw=1.6))
ax.add_patch(FancyBboxPatch((0.2, -3.0), 17.8, 0.9, boxstyle="round,pad=0.05", fc="#f1f5f9", ec="#94a3b8", lw=1.2))
ax.text(9.1, -2.55, "Logging wrapper around EVERY call → logs/run_log.jsonl · cost_report.csv · interventions.md        Cost: ₹0 (offline rules engine + free TTS; optional local Ollama LLM)", ha="center", va="center", fontsize=9.5, color="#334155")
ax.text(9.1, 3.0, "Somaiya AgentReel — multi-agent pipeline", ha="center", fontsize=15, weight="bold", color="#123c69")
fig.savefig(C.ROOT / "docs/agent_graph.png", dpi=130, bbox_inches="tight", facecolor="white")
print("saved docs/agent_graph.png")
