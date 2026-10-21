"""Agent 5 - Asset Generator: voice-over (free TTS), timeline, captions (.srt), raw music, asset manifest.
Visuals are procedural illustrations rendered by the Editor (nothing copyrighted, no faces)."""
import csv, json, re
from pathlib import Path
import numpy as np
import scipy.io.wavfile as wavfile
from core import tts, music, config as C

SR = 48000
LEAD, TAIL = 0.25, 0.35
DIGITS = "zero one two three four five six seven eight nine".split()


def speakable(text):
    """Written -> spoken form so TTS reads '1930' as digits and 'cybercrime.gov.in' as 'dot gov dot in'."""
    t = re.sub(r"\b[\w-]+(\.[\w-]+)+\b", lambda m: m.group(0).replace(".", " dot "), text)
    t = re.sub(r"\b\d{4,}\b", lambda m: " ".join(DIGITS[int(c)] for c in m.group(0)), t)
    keep = {"PIN", "POSH", "NEP", "CAP", "SCAM"}      # read as words; other ALL-CAPS acronyms are spelled out (OTP -> O T P)
    t = re.sub(r"\b[A-Z]{2,5}\b", lambda m: m.group(0).title() if m.group(0) in keep else " ".join(m.group(0)), t)
    return t.replace("₹", "rupees ")


def chunk_caption(text, max_words=9):
    parts = re.split(r"(?<=[.,;:?!])\s+", text.strip())
    out = []
    for p in parts:
        w = p.split()
        while len(w) > max_words:
            out.append(" ".join(w[:max_words])); w = w[max_words:]
        if w:
            out.append(" ".join(w))
    merged = []
    for c in out:   # avoid 1-2 word orphans
        if merged and len(c.split()) <= 2 and len((merged[-1] + " " + c).split()) <= max_words + 2:
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def run(plan, brief, script, storyboard, outdir, seed, logger):
    outdir = Path(outdir); (outdir / "assets").mkdir(parents=True, exist_ok=True)
    lines = {l["id"]: l for l in script["lines"]}
    vo_parts, shots = [], storyboard["shots"]
    t = 0.0
    caps, timings = [], {}
    for s in shots:
        if s["visual"] == "endcard":
            s["start"], s["duration_s"] = round(t, 3), plan["endcard_s"]
            break
        l = lines[s["script_line"]]
        spoken = speakable(l["text"])
        wav = logger.call("asset_generator", "tts", tts.provider_used, lambda sp=spoken: tts.synth_line(sp), prompt_id=f"vo:{l['id']}")
        dur = len(wav) / SR
        s["start"], s["duration_s"] = round(t, 3), round(LEAD + dur + TAIL, 3)
        vo_parts.append((t + LEAD, wav))
        timings[l["id"]] = (t + LEAD, t + LEAD + dur)
        ch = chunk_caption(l["text"])
        wts = np.array([len(c) for c in ch], float)
        edges = np.concatenate([[0], np.cumsum(wts) / wts.sum()]) * dur
        for c, a, b in zip(ch, edges[:-1], edges[1:]):
            caps.append({"start": round(t + LEAD + a, 3), "end": round(t + LEAD + b, 3), "text": c, "shot": s["id"]})
        t += s["duration_s"]
    total = s["start"] + s["duration_s"]
    n = int(total * SR) + SR
    vo = np.zeros(n, np.float32)
    for st, w in vo_parts:
        a = int(st * SR); vo[a:a + len(w)] += w
    wavfile.write(outdir / "assets/vo.wav", SR, (vo[: int(total * SR)] * 32767).astype(np.int16))
    mus = logger.call("asset_generator", "music_synth", "numpy-pad-v1", lambda: music.synth(total, seed=seed), prompt_id="music")
    wavfile.write(outdir / "assets/music.wav", SR, (mus * 32767).astype(np.int16))
    (outdir / "captions.json").write_text(json.dumps(caps, indent=1))
    with open(outdir / "captions.srt", "w", encoding="utf-8") as f:
        for i, c in enumerate(caps, 1):
            f.write(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n\n")
    # manifest (source + licence for every asset)
    with open(outdir / "assets/manifest.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["asset", "type", "source", "licence"])
        w.writerow(["assets/vo.wav", "voice-over", f"TTS: {tts.provider_used()}", "generated; free TTS (no real person's voice cloned)"])
        w.writerow(["assets/music.wav", "music", "synthesised in code (core/music.py, seed=%d)" % seed, "original work, CC0"])
        w.writerow(["illustrations (frames)", "images", "procedural drawing in core/visuals.py", "original work, CC0"])
        w.writerow(["assets/fonts/Poppins-*.ttf", "font", "Google Fonts: Poppins", "SIL Open Font License 1.1"])
        w.writerow(["assets/logo.png", "logo", "official Somaiya Vidyavihar logo supplied by the team (assets/logo_original.png; only empty margins cropped)", "institution-owned; used unmodified on a white card"])
    Path(C.ROOT / "assets").mkdir(exist_ok=True)
    (C.ROOT / "assets/manifest.csv").write_text((outdir / "assets/manifest.csv").read_text())
    return {"total_s": round(total, 3), "captions": caps, "timings": timings, "tts_provider": tts.provider_used()}
