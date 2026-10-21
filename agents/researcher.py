"""Agent 2 - Researcher (RAG): retrieve facts ONLY from data/ documents; every fact carries source + page."""
from core import rag, config as C


def run(plan, brief, data_dir=None):
    chunks = rag.ingest(data_dir or C.ROOT / "data")
    if not chunks:
        raise RuntimeError("no facts found in data/ — add the official fact sheet")
    bm = rag.BM25(chunks)
    found, gaps = {}, []
    for q in plan["queries"]:
        hits = bm.search(q, k=3)
        if not hits:
            gaps.append({"query": q, "reason": "no supporting source found"})
        for h in hits:
            if h["id"] not in found or h["score"] > found[h["id"]]["score"]:
                found[h["id"]] = dict(h, query=q)
    # must_include literals must literally exist in some source
    alltext = " ".join(c["claim"] for c in chunks).lower()
    for m in brief.get("must_include", []):
        if str(m).lower() not in alltext:
            gaps.append({"query": str(m), "reason": "must_include item not present in any provided document"})
    facts = sorted(found.values(), key=lambda f: f["id"])
    return {"facts": [{k: f.get(k) for k in ("id", "claim", "tags", "source", "page", "headline", "visual", "score", "query")} for f in facts],
            "gaps": gaps, "corpus_size": len(chunks)}
