"""Builds docs/process_report.pdf (1-2 pages) from the REAL logs of the latest practice run.  python -m tools.make_process_report"""
import csv, json
from collections import defaultdict
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from core import config as C

runs = sorted((C.ROOT / "outputs").glob("T00-A05-*"))
run = runs[-1]
summ = json.loads((run / "run_summary.json").read_text())
qa = json.loads((run / "qa_report.json").read_text())
script = json.loads((run / "script.json").read_text())
sdir = sorted((C.ROOT / "outputs").glob("T00-A95-*"))[-1]
stress = json.loads((sdir / "qa_report_loop0.json").read_text())
stress_final = json.loads((sdir / "run_summary.json").read_text())["measured"]["duration_s"]
rows = [r for r in csv.DictReader(open(C.ROOT / "logs/cost_report.csv")) if r["run_id"] == summ["run_id"]]
agg = defaultdict(lambda: [0, 0.0, 0.0])
for r in rows:
    a = agg[r["stage"]]; a[0] += 1; a[1] += float(r["latency_s"]); a[2] += float(r["cost_inr"])

ss = getSampleStyleSheet()
H = ParagraphStyle("h", parent=ss["Heading2"], fontSize=11, spaceBefore=6, spaceAfter=2, textColor=colors.HexColor("#123c69"))
B = ParagraphStyle("b", parent=ss["BodyText"], fontSize=8.6, leading=11)
doc = SimpleDocTemplate(str(C.ROOT / "docs/process_report.pdf"), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
f = [Paragraph("Somaiya AgentReel — Process Report", ss["Title"]),
     Paragraph(f"Team T00 · Brief A05 (Cyber safety) · run {summ['run_id']} · autonomy level <b>L3</b> (one mandatory human-review checkpoint) · seed {summ['seed']}", B)]
f += [Paragraph("1. Brief interpretation and creative strategy", H), Paragraph(
    "Audience: all students. Insight: scams work through fear, urgency and secrecy, so the video does the opposite — calm, practical, no scary imagery, no victims. "
    "Hook (first 3 s): the topic is named on screen and in voice (“Cyber safety. Four things every student must know.”). Body: one idea per shot, each with a clear icon and a 3-5 word headline. "
    "CTA: helpline 1930 and cybercrime.gov.in, repeated on the end card with the AI-disclosure line. Visuals are original procedural illustrations (no faces, no stock), music is synthesised in code, so licensing is clean.", B)]
f += [Paragraph("2. Agent graph, framework and models", H), Image(str(C.ROOT / "docs/agent_graph.png"), width=178 * mm, height=58 * mm), Paragraph(
    "Custom Python orchestrator (no framework lock-in): seven agents with JSON hand-offs validated by schemas. Researcher = BM25 over the fact sheet (every fact keeps source + page). "
    "Scriptwriter/Planner/Storyboarder = deterministic rules engine (free, reproducible); a local Ollama LLM can be switched on with LLM_PROVIDER=ollama, and its output is rejected and replaced by the rules engine if it cites unknown facts. "
    "Voice = Kokoro-82M neural TTS (free, offline on CPU; falls back to edge-tts, then espeak-ng). Editor = PIL frame renderer + ffmpeg (x264, AAC, two-pass loudnorm). Critic = 18 explicit checks.", B)]
t = [["Stage", "Calls", "Time (s)", "Cost (INR)"]] + [[k, v[0], f"{v[1]:.1f}", f"{v[2]:.2f}"] for k, v in agg.items()] + \
    [["TOTAL (wall clock)", sum(v[0] for v in agg.values()), f"{summ['wall_time_s']}", f"{summ['total_cost_inr']:.2f}"]]
tb = Table(t, colWidths=[60 * mm, 25 * mm, 30 * mm, 30 * mm])
tb.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123c69")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
f += [Paragraph("3. Time and cost per stage (from logs/cost_report.csv)", H), tb,
      Paragraph(f"Budget limit INR {C.BUDGET_INR:.0f}; spend INR {summ["total_cost_inr"]:.2f}. Output: {summ['measured']['duration_s']} s, {summ['measured']['lufs']} LUFS, {summ['measured']['size_mb']} MB, QA {sum(c['passed'] for c in qa['checks'])}/{len(qa['checks'])} checks passed.", B)]
fails = [c for c in stress["checks"] if not c["passed"]]
f += [Paragraph("4. Critic loop: what failed, what the agents fixed", H), Paragraph(
    f"The practice run passed first time (0 loops), so the loop was also stress-tested with a deliberately long brief (target 80 s, brief A95): the first render was "
    f"<b>{stress['measured']['duration_s']} s</b> → Critic failed <i>{', '.join(c['id'] for c in fails)}</i> and routed back to the Scriptwriter with a reduced word budget; the second pass was {stress_final} s and passed — no human involved. "
    "A negative test-suite (tests/test_critic_negative.py) proves the Critic rejects a wrong helpline, an invented URL, a made-up statistic, an uncited claim, template text and forbidden words. "
    "During the build the Critic's own checks also exposed a real bug: an unfilled TODO line in the fact sheet had been ingested as a ‘fact’; the parser now ignores comments and the Critic has a no_placeholders rule.", B)]
f += [Paragraph("5. Human interventions and how to remove them", H), Paragraph(
    f"Counted interventions during the run: {summ['human_interventions_counted']} (limit 5). The mandatory Category-A review checkpoint is logged separately and not counted; in rehearsal it was bypassed with --auto-approve-review "
    "(not allowed with --live). Next step to reach L4 for non-sensitive briefs: run the checkpoint only when the Critic reports any warning.", B)]
f += [Paragraph("6. Limitations, ethics, improvements", H), Paragraph(
    "• Facts are a draft from public national advisories — the official Somaiya fact sheet must replace data/fact_sheet.md before the Live Run (the official logo is already in use). "
    "• Voice is a neural but synthetic voice (Kokoro); no voice cloning of real people. • Captions are timed by character weight within each sentence (not forced alignment; Whisper would be tighter). "
    "• Digital-experience track and Hindi/Marathi subtitles are not implemented. • Safe messaging: no victims, no blame, contacts only from the sheet, AI disclosure on the end card, no personal data used.", B)]
doc.build(f)
print("saved docs/process_report.pdf")
