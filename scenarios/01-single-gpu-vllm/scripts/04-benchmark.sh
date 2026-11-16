#!/usr/bin/env bash
# Run ON the instance while vLLM is up. Benchmarks 1, 8 and 32 concurrent users.
# Flag names change between vLLM versions: check `docker exec vllm vllm bench serve --help`.
set -euo pipefail
LABEL="${1:-fp16}"
MODEL=$(curl -s localhost:8000/v1/models | python3 -c 'import json,sys;print(json.load(sys.stdin)["data"][0]["root"])')
mkdir -p results
for C in 1 8 32; do
  docker exec vllm vllm bench serve --model "$MODEL" --served-model-name llm \
    --dataset-name random --random-input-len 512 --random-output-len 256 \
    --num-prompts 200 --max-concurrency "$C" | tee "results/${LABEL}-c${C}.txt"
done
