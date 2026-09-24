"""Tone correction for his voice: less boom, more clarity.

The distilled Alfred voice learned its tone from the RVC recordings it was
trained on, and those were dull: 1-4 kHz, where speech gets its clarity, held
about 3% of the energy against about 15% for the stock Piper voice, and a fifth
of it sat under 150 Hz. The owner heard it as "underwater" (2026-09-24). Five
loudness-matched versions were put in front of him and he chose the strongest:
a high-pass at 120 Hz and a +12 dB shelf from 900 Hz.

Live it was worse than in the audition: the voice's own clicks came up with the
treble and he heard it as "super crackly" (2026-09-24). So the chain is no
longer fixed in code. It is read from ALFRED_VOICE_EQ_FILE, a small JSON file,
whenever that file changes - {"chain": [["highpass", 120, 0], ["highshelf", 900,
6]]} - and tuned while he listens, without restarting the server. No file, or
an empty chain, means the voice exactly as the model makes it.
"""

import json
import os
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

# The one he chose from the audition, kept for reference: (kind, Hz, dB).
CHOSEN = (("highpass", 120.0, 0.0), ("highshelf", 900.0, 12.0))
SETTINGS = Path(os.environ.get("ALFRED_VOICE_EQ_FILE", "/srv/storage/alfred/voice_eq.json"))
PEAK = 0.95
_cache = {"mtime": None, "chain": ()}


def current() -> tuple:
    """The chain in the settings file, re-read only when the file changes."""
    try:
        mtime = SETTINGS.stat().st_mtime
    except OSError:
        return ()
    if mtime != _cache["mtime"]:
        try:
            raw = json.loads(SETTINGS.read_text(encoding="utf-8")).get("chain") or []
            chain = tuple((str(k), float(f), float(g)) for k, f, g in raw)
            for kind, freq, gain in chain:
                biquad(kind, freq, gain, 48000)          # reject a bad entry now, not mid-sentence
        except (OSError, ValueError, TypeError):
            chain = ()                                   # a broken file means no EQ, never no voice
        _cache.update(mtime=mtime, chain=chain)
    return _cache["chain"]


def biquad(kind: str, freq: float, gain_db: float, rate: int, q: float = 0.707):
    """Filter coefficients from Robert Bristow-Johnson's audio EQ cookbook."""
    a_gain = 10 ** (gain_db / 40)
    w = 2 * np.pi * freq / rate
    cos, alpha = np.cos(w), np.sin(w) / (2 * q)
    if kind == "highpass":
        b = [(1 + cos) / 2, -(1 + cos), (1 + cos) / 2]
        a = [1 + alpha, -2 * cos, 1 - alpha]
    elif kind == "highshelf":
        s = 2 * np.sqrt(a_gain) * alpha
        b = [a_gain * ((a_gain + 1) + (a_gain - 1) * cos + s),
             -2 * a_gain * ((a_gain - 1) + (a_gain + 1) * cos),
             a_gain * ((a_gain + 1) + (a_gain - 1) * cos - s)]
        a = [(a_gain + 1) - (a_gain - 1) * cos + s,
             2 * ((a_gain - 1) - (a_gain + 1) * cos),
             (a_gain + 1) - (a_gain - 1) * cos - s]
    else:
        raise ValueError(f"unknown filter {kind!r}")
    return np.array(b) / a[0], np.array(a) / a[0]


def apply(samples: np.ndarray, rate: int, chain=CHOSEN) -> np.ndarray:
    """The samples through the chain, as loud as they came in, peaks kept under PEAK."""
    samples = np.asarray(samples, dtype=np.float64)
    if samples.size == 0 or not chain:
        return samples
    out = samples
    for kind, freq, gain in chain:
        b, a = biquad(kind, freq, gain, rate)
        out = lfilter(b, a, out)
    before, after = np.sqrt(np.mean(samples ** 2)), np.sqrt(np.mean(out ** 2))
    if after > 0:
        out = out * (before / after)
    peak = np.abs(out).max()
    if peak > PEAK:
        out = out * (PEAK / peak)
    return out
