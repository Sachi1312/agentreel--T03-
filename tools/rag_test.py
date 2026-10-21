#!/usr/bin/env python3
"""Step 2 of the lab procedure: test retrieval with 10 sample questions -> docs/rag_eval.md"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agents import researcher

QA = [("Can the police arrest me over a video call?", "F01"), ("Which number do I call to report cyber fraud?", "F11"),
      ("Someone threatens to leak my private photos unless I pay", "F07"), ("Should I give my OTP to a caller who says he is an officer?", "F04"),
      ("A job offer asks me to pay a registration fee first", "F05"), ("Do I need my UPI PIN to receive money?", "F06"),
      ("Should I delete the chat messages from the blackmailer?", "F08"), ("How fast should I report a payment fraud?", "F09"),
      ("Who do scammers pretend to be on calls?", "F02"), ("Is it my fault if I get scammed?", "F10")]
facts, sources = researcher.ingest(ROOT / "data")
idx = researcher.FactIndex(facts)
rows, hit1, hit3 = [], 0, 0
for q, exp in QA:
    top = idx.query(q)[:3]
    ids = [f["id"] for _, f in top]
    hit1 += ids[0] == exp
    hit3 += exp in ids
    rows.append(f"| {q} | {exp} | {', '.join(ids)} | {'yes' if ids[0] == exp else ('top-3' if exp in ids else 'NO')} |")
md = ["# Retrieval test (10 sample questions)", "", f"Corpus: {len(facts)} claims from {len(sources)} sources. Index: TF-IDF (1-2 grams), local.", "",
      "| question | expected | top-3 retrieved | hit |", "|---|---|---|---|", *rows, "",
      f"**top-1 accuracy {hit1}/10, top-3 accuracy {hit3}/10**"]
(ROOT / "docs" / "rag_eval.md").write_text("\n".join(md))
print("\n".join(md))
