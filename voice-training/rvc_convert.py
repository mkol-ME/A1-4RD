#!/usr/bin/env python3
"""Convert a WAV file to Alfred's selected RVC voice."""

import argparse
import time
from pathlib import Path

import torch
from rvc_python.infer import RVCInference

ROOT = Path(__file__).resolve().parent.parent   # project root, where the models live
MODEL = ROOT / "rvc-model" / "AlfredPennyworth_465e_8835s.pth"
INDEX = ROOT / "rvc-model" / "AlfredPennyworth.index"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--repeat", type=int, default=1, help=argparse.SUPPRESS)
    args = parser.parse_args()

    started = time.perf_counter()
    converter = RVCInference(
        device="cuda:0",
        model_path=str(MODEL),
        index_path=str(INDEX),
        version="v2",
    )
    converter.set_params(f0method="rmvpe", index_rate=0.7, protect=0.33)
    loaded = time.perf_counter()
    timings = []
    for _ in range(args.repeat):
        conversion_started = time.perf_counter()
        converter.infer_file(str(args.input), str(args.output))
        timings.append(time.perf_counter() - conversion_started)
    finished = time.perf_counter()

    allocated = torch.cuda.max_memory_allocated() / (1024 ** 2)
    reserved = torch.cuda.max_memory_reserved() / (1024 ** 2)
    print(f"load={loaded-started:.2f}s conversions={','.join(f'{value:.2f}s' for value in timings)} total={finished-started:.2f}s")
    print(f"peak_cuda_allocated={allocated:.0f}MiB peak_cuda_reserved={reserved:.0f}MiB")


if __name__ == "__main__":
    main()
