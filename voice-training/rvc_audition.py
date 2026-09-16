#!/usr/bin/env python3
"""Render the same lines through a grid of RVC settings, to be listened to.

The pipeline settings were never auditioned — index_rate 0.7 and protect 0.33
were the first values tried and have been in place since. This writes one file
per variant so they can be compared on the same sentences rather than argued
about. Run it on the box; it loads its own RVC on GPU 1 alongside the service.
"""

import shutil
import sys
import time
import wave
from pathlib import Path

from piper import PiperVoice
from rvc_python.infer import RVCInference

ROOT = Path(__file__).resolve().parent.parent   # project root, where the models live
PIPER_MODEL = ROOT / "tts-models" / "piper" / "en_GB-alan-medium.onnx"
RVC_DIR = ROOT / "rvc-model"
OUT = ROOT / "rvc-audition"

# Two lines: one flat and technical, one with a full stop that has to sit.
LINES = {
    "technical": "Set retraction to about forty millimetres per second, sir. "
                 "Anything slower and you will simply string across the gap.",
    "dry": "You said that last week, sir. "
           "I shall say nothing further about it.",
}

# name -> params layered over the current production settings.
BASE = dict(f0method="rmvpe", index_rate=0.7, protect=0.33, filter_radius=3, rms_mix_rate=1.0, f0up_key=0)
VARIANTS = {
    "00-current":          {},
    "01-index-0.4":        dict(index_rate=0.4),
    "02-index-0.2":        dict(index_rate=0.2),
    "03-index-0.0":        dict(index_rate=0.0),
    "04-protect-0.5":      dict(protect=0.5),
    "05-filter-radius-5":  dict(filter_radius=5),
    "06-rms-mix-0.25":     dict(rms_mix_rate=0.25),
    "07-pitch-down-2":     dict(f0up_key=-2),
    "08-index0.4-prot0.5": dict(index_rate=0.4, protect=0.5),
}


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    piper = PiperVoice.load(PIPER_MODEL, use_cuda=False)
    sources = {}
    for name, text in LINES.items():
        source = OUT / f"_carrier-{name}.wav"
        with wave.open(str(source), "wb") as handle:
            piper.synthesize_wav(text, handle)
        sources[name] = source
    print(f"carrier written for {len(sources)} line(s)", flush=True)

    rvc = RVCInference(
        device="cuda:0",
        model_path=str(RVC_DIR / "AlfredPennyworth_465e_8835s.pth"),
        index_path=str(RVC_DIR / "AlfredPennyworth.index"),
        version="v2",
    )

    for variant, overrides in VARIANTS.items():
        params = dict(BASE, **overrides)
        rvc.set_params(**params)
        for line, source in sources.items():
            target = OUT / f"{variant}__{line}.wav"
            started = time.perf_counter()
            rvc.infer_file(str(source), str(target))
            elapsed = time.perf_counter() - started
        detail = ", ".join(f"{k}={v}" for k, v in sorted(overrides.items())) or "unchanged"
        print(f"  {variant:22s} {elapsed:.2f}s  ({detail})", flush=True)

    print(f"\n{len(VARIANTS)} variants x {len(LINES)} lines -> {OUT}")


if __name__ == "__main__":
    main()
