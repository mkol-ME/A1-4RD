#!/usr/bin/env python3
"""Design original Alfred-like voice candidates without cloning an actor."""

import argparse
from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel

OUTPUT_DIR = Path(__file__).parent / "tts-samples-qwen"
TEXT = (
    "The first layer is lifting because the bed is losing heat at the corners, sir. "
    "An enclosure would help. Apparently the laws of thermodynamics remain unmoved by confidence."
)
PROFILES = {
    "alfred_a": (
        "An older male voice with a warm low baritone and a restrained mid-Atlantic accent. "
        "Cultivated but plain, unhurried, dryly amused, with precise consonants and quiet authority. "
        "Natural modern speech, never theatrical or exaggerated."
    ),
    "alfred_b": (
        "A dignified older gentleman with a mellow medium-low voice and subtle British inflection. "
        "Calm, observant, intimate, and understated, speaking at a measured pace with dry wit. "
        "Avoid a booming announcer voice and avoid costume-drama affectation."
    ),
    "alfred_c": (
        "A mature male household steward: composed, intelligent, slightly weary, and warmly sardonic. "
        "A smooth transatlantic baritone, crisp articulation, small pauses at full stops, and no melodrama."
    ),
    "alfred_d": (
        "An elderly gentleman in his late seventies with a naturally aged, medium-low voice. "
        "His tone is lean rather than booming, with faint breathiness and a subtle dry rasp from age. "
        "He has a restrained mid-Atlantic accent with gentle British coloring, precise consonants, "
        "a narrow pitch range, and quiet paternal warmth. He speaks conversationally and unhurriedly, "
        "lets full stops settle, and delivers the final joke as effortless understatement. "
        "Avoid a polished narrator, announcer, theatrical butler, or vigorous middle-aged sound."
    ),
    "alfred_e": (
        "An elderly upper-class English gentleman in his seventies, speaking unmistakable traditional "
        "Received Pronunciation. His voice is a cultivated medium-low baritone, naturally aged with "
        "light breath and a trace of dry rasp. Use crisp clipped consonants, carefully rounded vowels, "
        "non-rhotic pronunciation, and the effortless composure of old British nobility. The delivery is "
        "private and conversational, never projected: measured pace, narrow pitch range, quiet warmth, "
        "and a dry final aside. Sound posh and distinctly English without becoming a theatrical butler, "
        "a royal impersonation, or an announcer."
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("profiles", nargs="*", choices=PROFILES, default=list(PROFILES))
    args = parser.parse_args()
    torch.manual_seed(14)
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        device_map="cpu",
        dtype=torch.float32,
    )
    OUTPUT_DIR.mkdir(exist_ok=True)
    for name in args.profiles:
        description = PROFILES[name]
        waves, sample_rate = model.generate_voice_design(
            text=TEXT,
            language="English",
            instruct=description,
        )
        destination = OUTPUT_DIR / f"{name}.wav"
        sf.write(destination, waves[0], sample_rate)
        print(destination)


if __name__ == "__main__":
    main()
