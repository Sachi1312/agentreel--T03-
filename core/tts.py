"""Text-to-speech, free only. Default chain (TTS_PROVIDER=auto):
   1. Kokoro-82M (open-source neural voice, runs OFFLINE on any CPU; model auto-downloads once, ~115 MB)
   2. edge-tts   (free Microsoft online voice, no key)
   3. espeak-ng  (always available, robotic - last resort)"""
import asyncio, ctypes, re, subprocess, tempfile, urllib.request
from pathlib import Path
import numpy as np
from scipy.signal import resample_poly
from .config import env, ROOT

SR = 48000
MODEL_DIR = ROOT / "models"
KOKORO_FILES = {
    "kokoro-v1.0.int8.onnx": ("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx", 80_000_000),
    "voices-v1.0.bin": ("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin", 20_000_000),
}
_kokoro = None
_provider_used = None
_failed = set()


def _to48k(x, sr):
    g = int(np.gcd(SR, sr))
    return resample_poly(x, SR // g, sr // g).astype(np.float32)


# ---------------------------------------------------------------- kokoro
def ensure_models():
    MODEL_DIR.mkdir(exist_ok=True)
    for name, (url, min_size) in KOKORO_FILES.items():
        p = MODEL_DIR / name
        if not p.exists() or p.stat().st_size < min_size:
            print(f"  downloading {name} (one-time) ...")
            tmp = p.with_suffix(".part")
            urllib.request.urlretrieve(url, tmp)
            tmp.rename(p)


def _kokoro_say(text):
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        ensure_models()
        _kokoro = Kokoro(str(MODEL_DIR / "kokoro-v1.0.int8.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
    voice = env("KOKORO_VOICE", "af_heart")
    speed = float(env("KOKORO_SPEED", "0.98"))
    parts = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]
    out, gap = [], np.zeros(int(0.16 * 24000), np.float32)
    for i, s in enumerate(parts):
        x, sr = _kokoro.create(s, voice=voice, speed=speed, lang="en-us")
        out.append(np.asarray(x, np.float32))
        if i < len(parts) - 1:
            out.append(gap)
    return _to48k(np.concatenate(out), 24000), f"kokoro-v1.0-int8:{voice}"


# ---------------------------------------------------------------- edge-tts
def _edge_say(text):
    import edge_tts
    voice = env("TTS_VOICE", "en-IN-NeerjaNeural")

    async def go(path):
        await asyncio.wait_for(edge_tts.Communicate(text, voice).save(path), timeout=20)
    with tempfile.TemporaryDirectory() as d:
        mp3, wav = Path(d) / "a.mp3", Path(d) / "a.wav"
        asyncio.run(go(str(mp3)))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ar", str(SR), "-ac", "1", str(wav)], check=True)
        import scipy.io.wavfile as w
        _, x = w.read(wav)
    return x.astype(np.float32) / 32768.0, f"edge-tts:{voice}"


# ---------------------------------------------------------------- espeak (fallback)
def _espeak_say(text, voice="en-us", rate=165, pitch=45):
    import espeakng_loader
    lib = ctypes.CDLL(espeakng_loader.get_library_path())
    lib.espeak_Initialize.restype = ctypes.c_int
    sr = lib.espeak_Initialize(2, 0, espeakng_loader.get_data_path().encode(), 0)
    buf = []
    CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)

    def cb(wav, n, ev):
        if wav and n > 0:
            buf.append(np.ctypeslib.as_array(wav, shape=(n,)).copy())
        return 0
    cbf = CB(cb)
    lib.espeak_SetSynthCallback(cbf)
    lib.espeak_SetVoiceByName(voice.encode())
    lib.espeak_SetParameter(1, rate, 0)
    lib.espeak_SetParameter(3, pitch, 0)
    b = text.encode("utf-8")
    lib.espeak_Synth(b, len(b) + 1, 0, 1, 0, 1, None, None)
    lib.espeak_Synchronize()
    lib.espeak_Terminate()
    return _to48k(np.concatenate(buf).astype(np.float32) / 32768.0, sr), "espeak-ng"


# ---------------------------------------------------------------- public API
def _trim(x, thr=0.01, pad=0.06):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    return x[max(idx[0] - int(pad * SR), 0): min(idx[-1] + int(pad * SR), len(x))]


def synth_line(text):
    """Mono float32 @48 kHz. Tries providers in order; remembers which one worked."""
    global _provider_used
    prov = (env("TTS_PROVIDER", "auto") or "auto").lower()
    chain = {"auto": ["kokoro", "edge", "espeak"], "kokoro": ["kokoro", "espeak"], "edge": ["edge", "espeak"], "espeak": ["espeak"]}[prov]
    fn = {"kokoro": _kokoro_say, "edge": _edge_say, "espeak": _espeak_say}
    x = None
    for name in chain:
        if name in _failed:
            continue
        try:
            x, _provider_used = fn[name](text)
            break
        except Exception as e:
            _failed.add(name)
            print(f"  ! TTS provider '{name}' unavailable ({type(e).__name__}: {str(e)[:80]}) -> trying next")
    x = _trim(x)
    return x / max(np.abs(x).max(), 1e-6) * 0.9


def provider_used():
    return _provider_used
