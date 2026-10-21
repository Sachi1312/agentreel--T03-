# Somaiya AgentReel — Team T03

An autonomous multi-agent pipeline that turns a `brief.yaml` into a 30–60 s promotional/awareness video for Somaiya.
**Cost: ₹0** (no paid API anywhere). **Voice: Kokoro-82M neural TTS, offline, works on any laptop CPU (no GPU, no internet after a one-time ~115 MB model download).** **Autonomy level: L3** (end-to-end AI; one mandatory human-review checkpoint for safety/AI briefs).

Practice brief used: **A05 — Cyber safety** (digital-arrest scams, UPI & fake-job fraud, sextortion, helpline 1930).

## Run it (one command)
```bash
pip install -r requirements.txt          # + ffmpeg on PATH
python run.py --brief briefs/A05_practice.yaml --seed 42                       # asks you to approve at the review checkpoint
python run.py --brief briefs/A05_practice.yaml --seed 42 --auto-approve-review # REHEARSAL ONLY (blocked with --live)
```
Output: `outputs/T00_A05_final.mp4` (+ `.srt`, `qa_report.json`, script/facts/plan/storyboard), full per-run folder in `outputs/<run_id>/`, logs in `logs/`.
Team ID: set `TEAM_ID` in `.env` (copy `.env.example`) or pass `--team T07`.

## Pipeline (docs/agent_graph.png)
Brief → **Planner** → **Researcher (RAG)** → **Scriptwriter** → **Storyboarder** → **Asset Generator** → **Editor** → **Critic** → (fail: route back to the responsible agent, max 3 loops | pass: human review → export)

| Agent | File | What it does |
|---|---|---|
| Planner | `agents/planner.py` | reads brief, word budget, per-stage time/cost split, queries, success criteria → `plan.json` |
| Researcher | `agents/researcher.py` + `core/rag.py` | BM25 over `data/` (fact sheet `.md/.txt` and PDFs); each fact keeps source + page → `facts.json`; reports gaps |
| Scriptwriter | `agents/scriptwriter.py` | hook + body + CTA, each line cites fact IDs; rules engine, or local Ollama LLM (validated, falls back to rules) |
| Storyboarder | `agents/storyboarder.py` | 6–12 shots: visual, on-screen text, duration, asset source |
| Asset Generator | `agents/asset_generator.py` | neural voice-over (Kokoro → edge-tts → espeak fallback), timeline, captions + `.srt`, synthesised music, `manifest.csv` |
| Editor | `agents/editor.py` + `core/visuals.py` | frames, ducking, two-pass loudnorm (−14 LUFS), x264/AAC, captions, logo, end card, disclosure |
| Critic | `agents/critic.py` | 18 checkable rules on the real file (see below) → `qa_report.json` |
| Human review | `agents/human_review.py` | mandatory for categories A and C; not counted as an intervention |

**Critic rules:** fact grounding per line · every phone/URL/email exists in the fact sheet · no placeholder text · must_include / must_avoid · hook names topic · end card (logo, CTA, disclosure all rendered) · safe zones & caption ≥48 px (measured from rendered boxes) · storyboard coverage · duration 30–60 s · 1080×1920 · constant 30 fps · H.264 High yuv420p · AAC 48 kHz stereo 128–192 kbps · ≤100 MB · file name · −14 LUFS ±1.5 & true peak ≤ −1 dBTP · `.srt` present.

## Tests
```bash
python -m tests.test_retrieval          # 10 sample questions -> expected source IDs
python -m tests.test_critic_negative    # Critic must REJECT wrong helpline, invented URL, made-up stat, uncited claim, template text, banned words
python -m tests.test_llm_fallback       # hallucinated LLM output is rejected and replaced by the rules engine
```

## Results (practice run, see `docs/process_report.pdf` and `logs/`)
Three runs (`T00-A05-01/02/03`, seed 42, Kokoro voice): QA 18/18, 48.6 s, 1080×1920 @30 fps, −14.0 LUFS, ~5 MB, ₹0, 0 loops, ~4 min each on 2 CPU cores, and all three final MP4s are **byte-identical** (same SHA-256) → reproducible.
A deliberately over-long brief (`briefs/A05_stress_long.yaml`, run `T00-A95-01`) demonstrates the repair loop: Critic rejected a 62.2 s render, the Scriptwriter shortened it, second pass passed.

## ⚠ Before the Live Run — things only YOU can do
1. **Replace `data/fact_sheet.md`** with the official Somaiya fact sheet / brochure / policy PDFs you are given (drop PDFs in `data/`). The current file is a DRAFT compiled from public national cybercrime advisories — it contains no Somaiya-specific contact (none was invented).
2. **Logo:** the official Somaiya Vidyavihar logo you sent is already in `assets/logo.png` (original kept as `assets/logo_original.png`). It is shown unmodified on a white card because the maroon logo needs a light background. If the media kit provides a transparent/white version, drop it in as `assets/logo.png`.
3. For Category A/C briefs do the human review properly; `--auto-approve-review` is rehearsal-only.
4. Put your real team ID in `.env`, tag the repo `v1.0-build` 24 h before the Live Run, never commit `.env`.
5. **Voice:** default is Kokoro (natural, offline). `models/` is included in the zip; if missing it downloads itself on first run (or run `python -m tools.download_models` once on good wifi). Change voice with `KOKORO_VOICE` in `.env` (e.g. `bf_emma`, `am_michael`). Optional quality boost (still free): install Ollama + a small model and set `LLM_PROVIDER=ollama` for richer scripts (that path is implemented and unit-tested with a mock, but not exercised against a real model here).
6. The new brief's facts must exist in `data/`; topics with no matching facts are reported as research gaps rather than invented.

## Known limitations (honest list)
Voice is neural but still synthetic (~1x real-time on CPU) · captions timed by character weight, not forced alignment · video track only (no digital-experience track, no Hindi/Marathi subtitles) ·
rules-engine scripts read like the fact sheet (an LLM would paraphrase more naturally).

## Credits / licences
Poppins font (SIL OFL 1.1). Kokoro-82M voice model (Apache-2.0, https://github.com/thewh1teagle/kokoro-onnx). espeak-ng (GPL-3, fallback + phonemiser via `espeakng-loader`). Music and illustrations are generated by this code (CC0). No tutorial code copied.
