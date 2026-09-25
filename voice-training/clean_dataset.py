#!/usr/bin/env python3
"""Repair the clicks in a distilled dataset and correct its tone, before training.

The RVC voice clicks about seven times a second and holds almost nothing in
1-4 kHz; a Piper voice trained on it learned both (2026-09-24: "underwater",
then "super crackly" once the treble was lifted live). No RVC setting changed
either (index rate, protect, pitch filter and volume mix were all swept). So the
teacher audio is cleaned instead, and the voice learns clean audio:

  clicks    a sample whose second difference jumps far past its local level is
            patched, with ~1 ms around it replaced by a cubic curve through
            the samples either side: about 7.6 a second (see FACTOR).
  tone      brain/voice_eq, after the repair, so no click is brightened.
            1-4 kHz goes from 2.5% of the energy to about 15%, the stock voice's.

    python voice-training/clean_dataset.py voice-distill-v2 voice-distill-v2-clean [--eq strong|medium|none]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.interpolate import CubicSpline

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))
import voice_eq  # noqa: E402

EQ = {
    "strong": voice_eq.CHOSEN,
    "medium": (("highpass", 100.0, 0.0), ("highshelf", 1000.0, 9.0)),
    "none": (),
}


# Calibrated at the dataset's 22,050 Hz against the stock voice, which has no
# learned clicks: at 6 it flagged 21 a second even there (consonants, not
# clicks), at 8 it flags 2.5 in the stock voice against 7.6 in the RVC audio.
FACTOR = 8.0


def clicks(x: np.ndarray, rate: int, factor: float = FACTOR) -> np.ndarray:
    """Positions where the second difference is `factor` times its 10 ms average."""
    d = np.abs(np.diff(x, n=2))
    window = max(int(0.01 * rate), 1)
    local = np.convolve(d, np.ones(window) / window, mode="same") + 1e-6
    return np.flatnonzero(d > factor * local) + 1


def declick(x: np.ndarray, rate: int, half_ms: float = 0.6) -> tuple[np.ndarray, int]:
    """The clip with each click patched by a cubic curve, and how many were patched."""
    y = x.copy()
    hits = clicks(y, rate)
    if hits.size == 0:
        return y, 0
    half = max(int(half_ms / 1000 * rate), 2)
    regions, start, end = [], hits[0] - half, hits[0] + half
    for hit in hits[1:]:
        if hit - half <= end:
            end = hit + half
        else:
            regions.append((start, end))
            start, end = hit - half, hit + half
    regions.append((start, end))
    for lo, hi in regions:
        lo, hi = max(lo, 4), min(hi, len(y) - 5)
        if hi <= lo:
            continue
        support = np.r_[lo - 4:lo, hi + 1:hi + 5]
        y[lo:hi + 1] = CubicSpline(support, y[support])(np.arange(lo, hi + 1))
    return y, len(regions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--eq", choices=sorted(EQ), default="strong")
    args = parser.parse_args()

    (args.destination / "wav").mkdir(parents=True, exist_ok=True)
    rows = (args.source / "metadata.csv").read_text(encoding="utf-8").splitlines()
    patched = seconds = 0.0
    for number, row in enumerate(rows, 1):
        name = row.split("|", 1)[0]
        x, rate = sf.read(args.source / "wav" / name, dtype="float64")
        if x.ndim > 1:
            x = x.mean(axis=1)
        y, count = declick(x, rate)
        y = voice_eq.apply(y, rate, EQ[args.eq]) if EQ[args.eq] else y
        y = y * (0.95 / max(np.abs(y).max(), 1e-9))
        sf.write(args.destination / "wav" / name, y, rate, subtype="PCM_16")
        patched += count
        seconds += len(x) / rate
        if number % 250 == 0 or number == len(rows):
            print(f"cleaned {number}/{len(rows)}: {patched / seconds:.1f} clicks/s patched", flush=True)
    (args.destination / "metadata.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"wrote {args.destination} ({len(rows)} clips, eq {args.eq})")


if __name__ == "__main__":
    main()
