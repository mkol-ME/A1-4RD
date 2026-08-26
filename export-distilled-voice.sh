#!/usr/bin/env bash
# Export one checkpoint for audition. This does not change the live service.
set -euo pipefail

project_dir="$(cd "$(dirname "$0")" && pwd)"
training_dir="$project_dir/piper-training"
checkpoint="${1:?usage: $0 CHECKPOINT.ckpt}"
destination="$project_dir/tts-models/piper/en_GB-alfred-medium.onnx"

"$training_dir/venv/bin/python" -m piper.train.export_onnx \
    --checkpoint "$checkpoint" \
    --output-file "$destination"
cp "$training_dir/output/en_GB-alfred-medium.onnx.json" "$destination.json"
echo "Exported $destination (live service unchanged)."
