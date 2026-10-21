"""Agent 6 - Editor: renders frames, ducks music under the voice, normalises loudness (two-pass loudnorm),
encodes H.264/AAC with ffmpeg, burns captions + logo + end card + AI-disclosure line."""
import json, os, re, subprocess
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import scipy.io.wavfile as wavfile
from scipy.ndimage import uniform_filter1d
from core import config as C, visuals

SR = 48000
_R = None   # renderer shared with forked workers


def _enc_cmd(w, h, out):
    return ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(C.FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
            "-r", str(C.FPS), "-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-bf", "2", "-fps_mode", "cfr", str(out)]


def _render_chunk(args):
    k, f0, f1, w, h, out = args
    p = subprocess.Popen(_enc_cmd(w, h, out), stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(np.asarray(_R.frame(f / C.FPS)).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg chunk failed")
    return k


def _loudnorm(inp, out, target):
    base = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(inp), "-af"]
    r = subprocess.run(base + [f"loudnorm=I={target}:TP=-2.0:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    m = json.loads(re.findall(r"\{[^{}]*\}", r.stderr, re.S)[-1])
    f = (f"loudnorm=I={target}:TP=-2.0:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
         f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(base + [f, "-ar", str(SR), "-ac", "2", str(out), "-y"], check=True, capture_output=True)
    return m


def mix_audio(outdir, total, target):
    vo = wavfile.read(outdir / "assets/vo.wav")[1].astype(np.float32) / 32768
    mu = wavfile.read(outdir / "assets/music.wav")[1].astype(np.float32) / 32768
    n = int(total * SR)
    vo = np.pad(vo, (0, max(n - len(vo), 0)))[:n]
    mu = np.pad(mu, ((0, max(n - len(mu), 0)), (0, 0)))[:n]
    env = uniform_filter1d(np.abs(vo), int(0.12 * SR))
    active = np.clip(env / 0.03, 0, 1)
    active = uniform_filter1d(active, int(0.25 * SR))
    gain = 0.30 - 0.20 * active          # music sits ~15-20 dB under the voice while speaking
    mix = np.stack([vo, vo], 1) * 0.9 + mu * gain[:, None]
    mix = mix / max(np.abs(mix).max(), 1e-6) * 0.9
    raw = outdir / "assets/mix_raw.wav"  # intermediate; removed by run.py after export
    wavfile.write(raw, SR, (mix * 32767).astype(np.int16))
    return _loudnorm(raw, outdir / "assets/mix.wav", target)


def run(plan, brief, storyboard, assets, outdir, seed, team, fb=None, logger=None):
    global _R
    fb = fb or {}
    outdir = Path(outdir)
    w, h = C.FORMATS[plan["format"]]
    shots, caps, total = storyboard["shots"], assets["captions"], assets["total_s"]
    _R = visuals.Renderer(w, h, shots, caps, seed=seed)
    target = C.TARGET_LUFS + fb.get("lufs_offset", 0.0)
    ln = logger.call("editor", "ffmpeg", "loudnorm-2pass", lambda: mix_audio(outdir, total, target), prompt_id="mix")
    # layout pass: record text bboxes at representative times for the Critic's safe-zone check
    times = [(s["start"] + min(1.5, s["duration_s"] - 0.1)) for s in shots] + [(c["start"] + c["end"]) / 2 for c in caps]
    for t in times:
        _R.frame(t, record=True)
    (outdir / "layout_report.json").write_text(json.dumps({"w": w, "h": h, "safe": _R.lay["safe"], "items": _R.report}, indent=1))
    # render in parallel chunks (one ffmpeg per chunk) then concat
    nframes = int(round(total * C.FPS))
    bounds = [int(round(s["start"] * C.FPS)) for s in shots] + [nframes]
    tasks = [(k, bounds[k], bounds[k + 1], w, h, outdir / f"chunk_{k:02d}.mp4") for k in range(len(shots))]

    def render():
        with Pool(min(os.cpu_count() or 1, 4)) as p:
            list(p.imap_unordered(_render_chunk, tasks))
    logger.call("editor", "render+x264", "libx264", render, prompt_id="frames")
    lst = outdir / "chunks.txt"
    lst.write_text("".join(f"file '{t[5].name}'\n" for t in tasks))
    vid = outdir / "video_only.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vid)], check=True)
    final = outdir / f"{team}_{brief['id']}_final.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vid), "-i", str(outdir / "assets/mix.wav"), "-c:v", "copy",
                    "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "160k", "-t", f"{nframes / C.FPS:.3f}",
                    "-movflags", "+faststart", str(final)], check=True)
    for t in tasks:
        t[5].unlink(missing_ok=True)
    for f in (lst, vid):
        f.unlink(missing_ok=True)
    return {"final": str(final), "loudnorm_input": ln, "target_lufs": target}
