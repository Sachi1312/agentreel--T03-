"""Structured logging: one JSONL line per model/tool call + cost_report.csv + interventions.md."""
import csv, hashlib, json, time
from datetime import datetime
from pathlib import Path


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class RunLogger:
    def __init__(self, root, run_id):
        self.run_id = run_id
        self.dir = Path(root) / "logs"
        self.dir.mkdir(exist_ok=True, parents=True)
        self.jsonl = self.dir / "run_log.jsonl"
        self.cost_csv = self.dir / "cost_report.csv"
        self.interventions = self.dir / "interventions.md"
        if not self.cost_csv.exists():
            with open(self.cost_csv, "w", newline="") as f:
                csv.writer(f).writerow(["run_id", "stage", "provider", "model", "units", "unit_type", "latency_s", "cost_inr"])
        if not self.interventions.exists():
            self.interventions.write_text(
                "# Human interventions\n\nEvery manual change during a Live Run (max 5). Editing a generated file by hand = 1.\n\n"
                "| time | run_id | stage | what was changed | why | counted? |\n|---|---|---|---|---|---|\n")
        self.n_interventions = 0

    # -- core record -------------------------------------------------------
    def record(self, agent, tool, model, prompt_id=None, input_tokens=0, output_tokens=0,
               cost_inr=0.0, latency_s=0.0, status="ok", output_path=None,
               human_intervention=False, note=None):
        rec = {"ts": datetime.now().isoformat(timespec="seconds"), "run_id": self.run_id,
               "agent": agent, "tool": tool, "model": model, "prompt_id": prompt_id,
               "input_tokens": input_tokens, "output_tokens": output_tokens,
               "cost_inr": round(cost_inr, 4), "latency_s": round(latency_s, 3), "status": status,
               "output_path": str(output_path) if output_path else None,
               "output_sha256": sha256_file(output_path) if output_path and Path(output_path).is_file() else None,
               "human_intervention": human_intervention}
        if note:
            rec["note"] = note
        with open(self.jsonl, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        units = input_tokens + output_tokens
        with open(self.cost_csv, "a", newline="") as f:
            csv.writer(f).writerow([self.run_id, agent, tool, model, units or 1,
                                    "tokens" if units else "calls", round(latency_s, 3), round(cost_inr, 4)])
        return rec

    def call(self, agent, tool, model, fn, prompt_id=None, output_path=None, **kw):
        """Run fn(), time it, log it (also on failure), return its result."""
        t0 = time.time()
        try:
            res = fn()
        except Exception as e:
            self.record(agent, tool, model() if callable(model) else model, prompt_id, latency_s=time.time() - t0, status=f"error: {e}"[:200])
            raise
        op = output_path() if callable(output_path) else output_path
        model = model() if callable(model) else model
        self.record(agent, tool, model, prompt_id, latency_s=time.time() - t0, output_path=op, **kw)
        return res

    def add_intervention(self, stage, what, why, counted=True):
        if counted:
            self.n_interventions += 1
        with open(self.interventions, "a") as f:
            f.write(f"| {datetime.now().isoformat(timespec='seconds')} | {self.run_id} | {stage} | {what} | {why} | {'yes' if counted else 'no (mandatory review)'} |\n")
        self.record("human", "intervention", "human", status="ok", human_intervention=counted, note=f"{stage}: {what}")
