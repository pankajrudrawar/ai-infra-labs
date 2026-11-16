#!/usr/bin/env bash
# Run ON the instance. Starts vLLM with Llama 3.1 8B (16-bit) or the 4-bit AWQ model.
# Usage: HF_TOKEN=... ./02-serve-vllm.sh [fp16|awq]
set -euo pipefail
: "${HF_TOKEN:?Set HF_TOKEN (Hugging Face read token, Llama 3.1 license accepted)}"
case "${1:-fp16}" in
  fp16) MODEL=meta-llama/Llama-3.1-8B-Instruct ;;
  awq)  MODEL=hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4 ;;
  *) echo "usage: $0 [fp16|awq]"; exit 1 ;;
esac
docker rm -f vllm 2>/dev/null || true
docker run -d --name vllm --gpus all --ipc=host -p 8000:8000 \
  -v "$HOME/.cache/huggingface:/root/.cache/huggingface" -e HF_TOKEN \
  vllm/vllm-openai:latest \
  --model "$MODEL" --served-model-name llm --max-model-len 8192 --gpu-memory-utilization 0.90
echo "Started $MODEL. Watch: docker logs -f vllm   then: nvidia-smi"
