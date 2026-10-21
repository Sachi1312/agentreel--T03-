"""LLM access. Default provider 'rules' = no LLM (deterministic, offline, free).
'ollama' = local open model (free). Anything an LLM returns is validated; on failure the caller falls back to rules."""
import json, urllib.request
from .config import env


def provider():
    return (env("LLM_PROVIDER", "rules") or "rules").lower()


def model_name():
    return env("OLLAMA_MODEL", "llama3.1:8b") if provider() == "ollama" else "rule-engine-v1"


def available():
    if provider() != "ollama":
        return False
    try:
        urllib.request.urlopen(env("OLLAMA_URL", "http://localhost:11434") + "/api/tags", timeout=2)
        return True
    except Exception:
        return False


def generate_json(prompt, system="", seed=42):
    """Returns (parsed_json, input_tokens, output_tokens). Local model => cost 0."""
    body = json.dumps({"model": env("OLLAMA_MODEL", "llama3.1:8b"), "prompt": prompt, "system": system, "stream": False,
                       "format": "json", "options": {"seed": seed, "temperature": 0.4}}).encode()
    req = urllib.request.Request(env("OLLAMA_URL", "http://localhost:11434") + "/api/generate", body,
                                 {"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=300).read())
    return json.loads(r["response"]), r.get("prompt_eval_count", 0), r.get("eval_count", 0)
