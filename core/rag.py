"""Tiny offline RAG: ingest fact sheet (+ PDFs), BM25 retrieval, every hit carries a source ID."""
import math, re
from collections import Counter
from pathlib import Path

LINE_RE = re.compile(r"^\[(?P<id>[A-Za-z]\w*)\]\s*(?:\{(?P<tags>[^}]*)\}\s*)?(?P<rest>.+)$")
STOP = set("a an the of to and or is are be it in on for you your with that this as at by from not no do can any more if so".split())


def tokenize(text):
    out = []
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in STOP:
            continue
        for suf in ("ing", "ed", "es", "s"):
            if len(w) > 4 and w.endswith(suf):
                w = w[: -len(suf)]
                break
        out.append(w)
    return out


def parse_fact_line(line):
    m = LINE_RE.match(line.strip())
    if not m:
        return None
    parts = [p.strip() for p in m.group("rest").split(" | ")]
    d = {"id": m.group("id"), "claim": parts[0], "tags": [t.strip() for t in (m.group("tags") or "").split(",") if t.strip()],
         "source": "unknown", "page": None, "headline": None, "visual": None}
    for p in parts[1:]:
        if ":" in p:
            k, v = p.split(":", 1)
            k = k.strip().lower()
            if k in ("source", "page", "headline", "visual"):
                d[k] = v.strip()
    return d


def ingest(data_dir):
    """Return list of chunks: {id, claim, tags, source, page, headline, visual}."""
    chunks = []
    for p in sorted(Path(data_dir).glob("*")):
        if p.suffix.lower() in (".md", ".txt"):
            text = re.sub(r"<!--.*?-->", "", p.read_text(encoding="utf-8"), flags=re.S)   # ignore comments / TODO examples
            for line in text.splitlines():
                if line.strip().startswith("["):
                    c = parse_fact_line(line)
                    if c and not re.search(r"<[^>]+>|\bTODO\b|PLACEHOLDER", c["claim"]):   # never ingest unfilled templates
                        c["doc"] = p.name
                        chunks.append(c)
        elif p.suffix.lower() == ".pdf":
            import pdfplumber
            with pdfplumber.open(p) as pdf:
                for pi, page in enumerate(pdf.pages, 1):
                    for ni, para in enumerate(re.split(r"\n\s*\n", page.extract_text() or "")):
                        para = " ".join(para.split())
                        if len(para) > 40:
                            chunks.append({"id": f"{p.stem[:12]}-p{pi}-{ni}", "claim": para, "tags": [], "source": p.name,
                                           "page": str(pi), "headline": None, "visual": None, "doc": p.name})
    return chunks


class BM25:
    def __init__(self, chunks, k1=1.5, b=0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.docs = [tokenize(c["claim"] + " " + " ".join(c["tags"]) + " " + (c.get("headline") or "")) for c in chunks]
        self.avg = sum(map(len, self.docs)) / max(len(self.docs), 1)
        df = Counter(t for d in self.docs for t in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - v + 0.5) / (v + 0.5)) for t, v in df.items()}

    def search(self, query, k=4, min_score=0.3):
        q = tokenize(query)
        res = []
        for c, d in zip(self.chunks, self.docs):
            tf = Counter(d)
            s = 0.0
            for t in q:
                if t in tf:
                    s += self.idf.get(t, 0) * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * (1 - self.b + self.b * len(d) / (self.avg or 1)))
            if s >= min_score:
                res.append((s, c))
        res.sort(key=lambda x: -x[0])
        return [dict(c, score=round(s, 3)) for s, c in res[:k]]
