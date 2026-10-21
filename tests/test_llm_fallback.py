"""LLM path is validated: a hallucinated fact id must be rejected and fall back to rules.  python -m tests.test_llm_fallback"""
import json, sys
from unittest import mock
from agents import scriptwriter
from core import llm, config as C
import yaml

OUT = sorted((C.ROOT / "outputs").glob("T00-A05-*"))[-1]
plan, facts = json.loads((OUT / "plan.json").read_text()), json.loads((OUT / "facts.json").read_text())
brief = yaml.safe_load((OUT / "brief.yaml").read_text())
bad = ({"lines": [{"role": "hook", "text": "Hi", "fact_ids": []}, {"role": "body", "text": "Made up.", "fact_ids": ["F99"]}]}, 10, 5)
with mock.patch.object(llm, "available", return_value=True), mock.patch.object(llm, "generate_json", return_value=bad):
    s = scriptwriter.run(plan, brief, facts)
print("method after bad LLM output:", s["method"])
sys.exit(0 if s["method"] == "rules" else 1)
