"""Original background music synthesised in code (numpy) => no licence issues. Soft pad + gentle arpeggio."""
import numpy as np

SR = 48000
CHORDS = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]  # Am F C G


def _hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def synth(duration, seed=42, bpm=84):
    rng = np.random.default_rng(seed)
    n = int(duration * SR)
    t = np.arange(n) / SR
    out = np.zeros((n, 2), dtype=np.float32)
    bar = 4 * 60.0 / bpm
    for i in range(int(duration / bar) + 1):
        t0, t1 = i * bar, (i + 1) * bar + 0.8
        a, b = int(t0 * SR), min(int(t1 * SR), n)
        if a >= n:
            break
        seg = np.arange(b - a) / SR
        env = np.minimum(seg / 0.6, 1) * np.minimum((t1 - t0 - seg) / 0.8, 1).clip(0, 1)
        ch = CHORDS[i % 4]
        pad = sum(np.sin(2 * np.pi * _hz(m - 12) * seg) + 0.4 * np.sin(2 * np.pi * _hz(m) * seg + 0.3) for m in ch)
        out[a:b] += (0.07 * env * pad)[:, None]
        step = 60.0 / bpm / 2
        for k in range(8):
            ts = t0 + k * step
            idx = int(ts * SR)
            if idx >= n:
                break
            note = ch[[0, 1, 2, 1, 2, 1, 0, 2][k]] + 12
            L = min(int(0.9 * SR), n - idx)
            s2 = np.arange(L) / SR
            pluck = np.sin(2 * np.pi * _hz(note) * s2) * np.exp(-s2 * 4.5) * (0.05 + 0.03 * rng.random())
            pan = 0.35 + 0.3 * rng.random()
            out[idx:idx + L, 0] += (pluck * (1 - pan)).astype(np.float32)
            out[idx:idx + L, 1] += (pluck * pan).astype(np.float32)
    fade = np.minimum(t / 1.0, 1) * np.minimum((duration - t) / 1.5, 1).clip(0, 1)
    out *= fade[:, None].astype(np.float32)
    return out / max(np.abs(out).max(), 1e-6) * 0.8
