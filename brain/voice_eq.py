"""Tone correction for his voice: less boom, more clarity.

The distilled Alfred voice learned its tone from the RVC recordings it was
trained on, and those were dull: 1-4 kHz, where speech gets its clarity, held
about 3% of the energy against about 15% for the stock Piper voice, and a fifth
of it sat under 150 Hz. The owner heard it as "underwater" (2026-09-24). Five
loudness-matched versions were put in front of him and he chose the strongest:
a high-pass at 120 Hz and a +12 dB shelf from 900 Hz.

Applied per sentence after resampling, so it costs a millisecond or two. Set
ALFRED_VOICE_EQ=off to hear the voice as the model makes it.
"""

import os

import numpy as np
from scipy.signal import lfilter

# (kind, frequency in Hz, gain in dB)
CHAIN = (("highpass", 120.0, 0.0), ("highshelf", 900.0, 12.0))
ENABLED = os.environ.get("ALFRED_VOICE_EQ", "on").lower() not in ("off", "0", "false", "no")
PEAK = 0.95


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


def apply(samples: np.ndarray, rate: int, chain=CHAIN) -> np.ndarray:
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
