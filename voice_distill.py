#!/usr/bin/env python3
"""Distil the Piper -> RVC chain into a labelled single-speaker dataset.

Run this on the inference box with the existing RVC environment.  Rendering is
resumable: completed WAV files are retained and metadata.csv is rebuilt from
the clips which passed validation.
"""

import argparse
import gzip
import json
import random
import re
import tempfile
import urllib.request
import wave
from pathlib import Path

import numpy as np
import soundfile as sf
from piper import PiperVoice
from rvc_python.infer import RVCInference
from scipy.signal import resample_poly


ROOT = Path(__file__).parent
PIPER_MODEL = ROOT / "tts-models" / "piper" / "en_GB-alan-medium.onnx"
RVC_DIR = ROOT / "rvc-model"
OUTPUT_DIR = ROOT / "voice-distill"
PROMPTS_URL = (
    "https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/"
    "en/en_GB/alan/medium/dataset.jsonl.gz?download=true"
)
TARGET_RATE = 22050  # matches the medium checkpoint used for fine-tuning
MIN_SECONDS = 0.45
MAX_SECONDS = 12.0


def fetch_prompts(limit: int, seed: int) -> list[str]:
    """Use the source voice's public training transcript as broad English text."""
    with urllib.request.urlopen(PROMPTS_URL, timeout=60) as response:
        with gzip.GzipFile(fileobj=response) as archive:
            prompts = [json.loads(line)["text"].strip() for line in archive if line.strip()]
    prompts = list(dict.fromkeys(p for p in prompts if 3 <= len(p.split()) <= 24))
    random.Random(seed).shuffle(prompts)
    return prompts[:limit]


def safe_text(text: str) -> str:
    # Piper metadata uses a pipe delimiter and one record per line.
    return re.sub(r"\s+", " ", text.replace("|", ",")).strip()


def convert_rate(source: Path, destination: Path) -> float:
    samples, rate = sf.read(source, dtype="float32", always_2d=False)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    if rate != TARGET_RATE:
        divisor = np.gcd(rate, TARGET_RATE)
        samples = resample_poly(samples, TARGET_RATE // divisor, rate // divisor)
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if peak > 0.99:
        samples = samples * (0.98 / peak)
    sf.write(destination, samples, TARGET_RATE, subtype="PCM_16")
    return len(samples) / TARGET_RATE


def render(limit: int, seed: int, output_dir: Path) -> None:
    audio_dir = output_dir / "wav"
    audio_dir.mkdir(parents=True, exist_ok=True)
    prompts = fetch_prompts(limit, seed)

    carrier = PiperVoice.load(PIPER_MODEL, use_cuda=False)
    converter = RVCInference(
        device="cuda:0",
        model_path=str(RVC_DIR / "AlfredPennyworth_465e_8835s.pth"),
        index_path=str(RVC_DIR / "AlfredPennyworth.index"),
        version="v2",
    )
    converter.set_params(f0method="rmvpe", index_rate=0.7, protect=0.33)

    accepted = []
    with tempfile.TemporaryDirectory(prefix="alfred-distill-") as temporary:
        temporary = Path(temporary)
        carrier_wav = temporary / "carrier.wav"
        converted_wav = temporary / "converted.wav"
        for number, text in enumerate(prompts, 1):
            name = f"alfred_{number:05d}.wav"
            destination = audio_dir / name
            duration = 0.0
            if destination.exists():
                with wave.open(str(destination), "rb") as clip:
                    duration = clip.getnframes() / clip.getframerate()
            else:
                with wave.open(str(carrier_wav), "wb") as handle:
                    carrier.synthesize_wav(text, handle)
                converter.infer_file(str(carrier_wav), str(converted_wav))
                duration = convert_rate(converted_wav, destination)
            if MIN_SECONDS <= duration <= MAX_SECONDS:
                accepted.append((name, safe_text(text)))
            else:
                destination.unlink(missing_ok=True)
                print(f"rejected {name}: {duration:.2f}s", flush=True)
            if number % 25 == 0 or number == len(prompts):
                print(f"rendered {number}/{len(prompts)}; accepted {len(accepted)}", flush=True)

    metadata = output_dir / "metadata.csv"
    metadata.write_text("".join(f"{name}|{text}\n" for name, text in accepted), encoding="utf-8")
    print(f"wrote {metadata} with {len(accepted)} clips")


def audit(output_dir: Path) -> None:
    rows = []
    metadata = output_dir / "metadata.csv"
    for line in metadata.read_text(encoding="utf-8").splitlines():
        name, text = line.split("|", 1)
        with sf.SoundFile(output_dir / "wav" / name) as clip:
            rows.append((len(clip) / clip.samplerate, text))
    durations = np.array([duration for duration, _ in rows])
    print(f"clips={len(rows)} hours={durations.sum() / 3600:.2f}")
    print(f"duration min={durations.min():.2f}s median={np.median(durations):.2f}s max={durations.max():.2f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--clips", type=int, default=1200)
    render_parser.add_argument("--seed", type=int, default=465)
    render_parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    audit_parser = subparsers.add_parser("audit")
    audit_parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    if args.command == "render":
        render(args.clips, args.seed, args.output)
    else:
        audit(args.output)


if __name__ == "__main__":
    main()
