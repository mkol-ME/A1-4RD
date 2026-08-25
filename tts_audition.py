#!/usr/bin/env python3
"""Generate comparable Alfred voice samples with Kokoro ONNX."""

from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).parent
MODEL_DIR = ROOT / "tts-models"
OUTPUT_DIR = ROOT / "tts-samples"
VOICES = ("bm_daniel", "bm_fable", "bm_george", "bm_lewis")
TEXT = (
    "The first layer is lifting because the bed is losing heat at the corners, sir. "
    "An enclosure would help. Apparently the laws of thermodynamics remain unmoved by confidence."
)


def main() -> None:
    model = Kokoro(MODEL_DIR / "kokoro-v1.0.onnx", MODEL_DIR / "voices-v1.0.bin")
    OUTPUT_DIR.mkdir(exist_ok=True)
    for voice in VOICES:
        samples, sample_rate = model.create(TEXT, voice=voice, speed=0.90, lang="en-gb")
        destination = OUTPUT_DIR / f"{voice}.wav"
        sf.write(destination, samples, sample_rate)
        print(destination)


if __name__ == "__main__":
    main()
