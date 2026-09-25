#!/usr/bin/env bash
# Prepare and fine-tune the one-stage Alfred Piper voice on the inference box.
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
training_dir="$project_dir/piper-training"
# Overridable so a second voice can be trained beside the live one without touching it.
dataset_dir="${DATASET_DIR:-$project_dir/voice-distill}"
output_dir="${OUTPUT_DIR:-$training_dir/output}"
epochs="${EPOCHS:-20}"
checkpoint="$training_dir/en_GB-alan-medium.ckpt"
checkpoint_url="https://huggingface.co/datasets/rhasspy/piper-checkpoints/resolve/main/en/en_GB/alan/medium/epoch%3D6339-step%3D1647790.ckpt?download=true"

if [[ ! -d "$training_dir/piper1-gpl/.git" ]]; then
    mkdir -p "$training_dir"
    git clone --depth 1 https://github.com/OHF-Voice/piper1-gpl.git "$training_dir/piper1-gpl"
fi
if [[ ! -x "$training_dir/venv/bin/pip" ]]; then
    # The headless box has no Debian python3-venv package and no sudo access.
    # Bootstrap virtualenv from the already isolated RVC environment instead.
    rm -rf "$training_dir/venv"
    "$project_dir/.venv-rvc/bin/python" -m pip install virtualenv
    "$project_dir/.venv-rvc/bin/python" -m virtualenv "$training_dir/venv"
    "$training_dir/venv/bin/pip" install -e "$training_dir/piper1-gpl[train]"
fi
if [[ ! -f "$training_dir/.torch-cu118" ]]; then
    # Current PyTorch CUDA 13 wheels dropped Pascal (sm_61).  CUDA 11.8 is the
    # newest official wheel known to execute on this box's GTX 1060.
    "$training_dir/venv/bin/pip" install --force-reinstall \
        torch==2.1.1 torchaudio==2.1.1 \
        --index-url https://download.pytorch.org/whl/cu118
    "$training_dir/venv/bin/pip" install "numpy<2"
    touch "$training_dir/.torch-cu118"
fi
if [[ ! -f "$training_dir/.piper-built" ]]; then
    "$training_dir/venv/bin/pip" install scikit-build cmake ninja
    export PATH="$training_dir/venv/bin:$PATH"
    (cd "$training_dir/piper1-gpl" && ./build_monotonic_align.sh)
    (cd "$training_dir/piper1-gpl" && "$training_dir/venv/bin/python" setup.py build_ext --inplace)
    touch "$training_dir/.piper-built"
fi
if [[ ! -f "$checkpoint" ]]; then
    wget -O "$checkpoint.part" "$checkpoint_url"
    mv "$checkpoint.part" "$checkpoint"
fi

if [[ "${1:-}" == "--setup-only" ]]; then
    echo "Piper training environment and warm-start checkpoint are ready."
    exit 0
fi

mkdir -p "$output_dir/cache"
export CUDA_VISIBLE_DEVICES=0
cd "$output_dir"
# The 1060 has 6 GB; a small batch is slower but avoids late-run OOMs.
"$training_dir/venv/bin/python" -m piper.train fit \
    --data.voice_name alfred \
    --data.csv_path "$dataset_dir/metadata.csv" \
    --data.audio_dir "$dataset_dir/wav" \
    --model.sample_rate 22050 \
    --data.espeak_voice en-gb-x-rp \
    --data.cache_dir "$output_dir/cache" \
    --data.config_path "$output_dir/en_GB-alfred-medium.onnx.json" \
    --data.batch_size 4 \
    --data.num_workers 4 \
    --trainer.max_epochs "$epochs" \
    --trainer.accelerator gpu \
    --trainer.devices 1 \
    --trainer.precision 32-true \
    --model.warmstart_ckpt "$checkpoint"
