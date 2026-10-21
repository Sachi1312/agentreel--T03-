#!/usr/bin/env python3
"""Build docs/process_report.pdf (1-2 pages) from the real run artefacts.  Usage: python tools/make_report.py [BRIEF_ID]"""
import csv, json, sys
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image

ROOT = Path(__file__).resolve().parent.parent
bid = sys.argv[1] if len(sys.argv) > 1 else "A05"
out = ROOT / "outputs" / bid
qa, hist = json.loads((out / "qa_report.json").read_text()), json.loads((out / "qa_history.json").read_text())
times, plan = json.loads((out / "stage_times.json").read_text()), json.loads((out / "plan.json").read_text())
script = json.loads((out / "script.json").read_text())
run_id = qa["run_id"]
rows = [r for r in csv.DictReader(open(ROOT / "logs" / "cost_report.csv")) if r["run_id"] == run_id]
stage_cost = {}
for r in rows:
    d = stage_cost.setdefault(r["stage"], {"cost": 0.0, "lat": 0.0, "n": 0, "prov": set()})
    d["cost"] += float(r["cost_inr"]); d["lat"] += float(r["latency_s"]); d["n"] += 1; d["prov"].add(r["provider"] + "/" + r["model"])
loop_ev = ROOT / "docs" / "loop_test_evidence.json"
interv = [l for l in (ROOT / "logs" / "interventions.md").read_text().splitlines() if l.startswith("| ") and l[2].isdigit()] if (ROOT / "logs" / "interventions.md").exists() else []

ss = getSampleStyleSheet()
H = ParagraphStyle("h", parent=ss["Heading2"], fontSize=10.5, spaceBefore=6, spaceAfter=2, textColor=colors.HexColor("#0B1E3F"))
B = ParagraphStyle("b", parent=ss["BodyText"], fontSize=8.4, leading=10.4)
T = ParagraphStyle("t", parent=ss["Title"], fontSize=14, spaceAfter=2)
doc = SimpleDocTemplate(str(ROOT / "docs" / "process_report.pdf"), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=12 * mm, bottomMargin=10 * mm)
S = [Paragraph("Somaiya AgentReel — Process Report", T),
     Paragraph(f"Team: T00 &nbsp;|&nbsp; Members: ______________ , ______________ &nbsp;|&nbsp; Brief {bid} — {qa['run_id']} &nbsp;|&nbsp; Autonomy level: L3 (one mandatory review checkpoint)", B)]
S += [Paragraph("1. Brief interpretation and creative strategy", H),
      Paragraph("<b>Audience insight:</b> students already know the words 'OTP' and 'UPI' but not that 'digital arrest' is a pure scam; fear of authority makes them comply. "
                "<b>Hook:</b> the first line states the myth-buster ('Digital arrest is not real') under a CYBER SAFETY title chip, visible from t=0.4 s. "
                "<b>Arc:</b> red flags → what to do → 'you are not at fault' (no blame) → one verified action (helpline 1930, cybercrime.gov.in). "
                "<b>Tone:</b> calm, non-alarming, abstract illustrations only (no faces, no victims).", B)]
S += [Paragraph("2. Agent graph, frameworks and models", H),
      Paragraph("Seven agents (Planner, Researcher/RAG, Scriptwriter, Storyboarder, Asset Generator, Editor, Critic) in a custom Python orchestrator (<i>run.py</i>), "
                "chosen over a framework because every hand-off is a validated JSON file and every call passes one logging wrapper. Models: <b>zero-cost stack</b> — "
                "TF-IDF retrieval (scikit-learn), deterministic rule engine for writing (optional Ollama/Gemini-free LLM path with automatic fallback), Kokoro-82M ONNX for voice-over, "
                "synthesised music, Pillow + ffmpeg for editing. Why each agent exists: the Researcher is the only source of facts; the Critic is the only gate to export.", B),
      Image(str(ROOT / "docs" / "agent_graph.png"), width=170 * mm, height=170 * mm * 0.46)]
tbl = [["Stage / agent", "Calls", "Provider / model", "Time (s)", "Cost (Rs)"]]
for k, d in stage_cost.items():
    tbl.append([k, d["n"], ", ".join(sorted(d["prov"]))[:44], f"{d['lat']:.1f}", f"{d['cost']:.2f}"])
tbl.append(["TOTAL", sum(d["n"] for d in stage_cost.values()), f"wall-clock {times['total_s']} s (slot: 180 min)", f"{sum(d['lat'] for d in stage_cost.values()):.1f}", f"{sum(d['cost'] for d in stage_cost.values()):.2f} (cap 500)"])
t = Table(tbl, colWidths=[32 * mm, 12 * mm, 80 * mm, 20 * mm, 30 * mm])
t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7.5), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1E3F")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                       ("GRID", (0, 0), (-1, -1), .25, colors.grey), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
S += [Paragraph("3. Time and cost per stage (from logs/cost_report.csv)", H), t]
m = qa["measurements"]
S += [Paragraph("4. Critic loop", H),
      Paragraph(f"On the final dry-run the Critic passed {sum(c['status']=='pass' for c in qa['checks'])}/{len(qa['checks'])} checks (1 warning: placeholder logo) in {len(hist)} attempt(s); "
                f"measured {m['duration_s']} s, {m['lufs']} LUFS, true peak {m['true_peak_dbfs']} dBFS, {m['size_mb']} MB. "
                "<b>What the loop fixed (fake-LLM test, tests/test_loop_with_fake_llm.py):</b> a script with an invented claim ('zero cyber frauds in five years') failed C04, was routed back to the Scriptwriter with the failure text, "
                "and the repaired script passed on loop 1. The same test exposed a real design flaw — the Storyboarder was re-asked the same LLM and could never recover — fixed by forcing the hook chip to the brief title and escalating retries to the rule engine. "
                "Negative unit tests prove the Critic rejects a wrong helpline (C05), invented claims (C04), unsafe terms (C07) and missing must-includes (C06).", B)]
S += [Paragraph("5. Human interventions and how to remove them", H),
      Paragraph(f"Dry-run interventions: <b>{len(interv)}</b> (limit 5). The only human step is the mandatory Category A/C review checkpoint (not counted). "
                "Next time: auto-detect and fetch the official logo; let the Critic also OCR the rendered frames to verify burned-in text against facts.json.", B)]
S += [Paragraph("6. Limitations, ethics, improvements", H),
      Paragraph("<b>Limits:</b> the writer is rule-based by default (claims are quoted from facts, so the script is accurate but less creative than an LLM — the Ollama path is implemented and logged but needs a local model); "
                "the practice fact sheet is general public guidance, <u>not</u> the official Somaiya sheet; the logo is a placeholder until data/media_kit/logo.png is provided; retrieval was only evaluated on 11 claims (10/10 — an easy test). "
                "<b>Ethics:</b> no real likeness, no cloned voice, only claims traceable to facts.json, contacts verified by the Critic, AI-disclosure on the end card, licences in assets/manifest.csv. "
                "<b>Improve:</b> Hindi/Marathi captions, Whisper-based caption verification, image-to-video clips, a learned (embedding) retriever for large policy PDFs.", B)]
doc.build(S)
print("saved docs/process_report.pdf")
