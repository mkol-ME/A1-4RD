#!/usr/bin/env python3
"""Transcribe an audio file locally on the dedicated Whisper GPU."""

import argparse
import sys
from pathlib import Path

from faster_whisper import WhisperModel


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path, help="audio file to transcribe")
    parser.add_argument("--model", default="small.en", help="Whisper model (default: small.en)")
    parser.add_argument("--language", default="en", help="language code (default: en)")
    args = parser.parse_args()

    if not args.audio.is_file():
        parser.error(f"audio file not found: {args.audio}")

    model = WhisperModel(args.model, device="cuda", compute_type="int8_float32")
    segments, info = model.transcribe(
        str(args.audio),
        language=args.language,
        beam_size=5,
        vad_filter=True,
    )

    print(f"language={info.language} probability={info.language_probability:.3f}", file=sys.stderr)
    for segment in segments:
        print(segment.text.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
