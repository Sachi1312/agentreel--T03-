"""Handout step 2: test retrieval with 10 sample questions.   python -m tests.test_retrieval"""
import json, sys
from core import rag, config as C

chunks = rag.ingest(C.ROOT / "data")
bm = rag.BM25(chunks)
samples = json.loads((C.ROOT / "tests/retrieval_samples.json").read_text())
ok = 0
for s in samples:
    top = [h["id"] for h in bm.search(s["q"], k=3)]
    hit = bool(set(top) & set(s["expect"]))
    ok += hit
    print(("PASS" if hit else "FAIL"), s["q"], "->", top)
print(f"{ok}/{len(samples)} questions retrieved the expected source in top-3")
sys.exit(0 if ok == len(samples) else 1)
