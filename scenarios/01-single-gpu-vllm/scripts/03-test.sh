#!/usr/bin/env bash
# Sends one chat request to the local vLLM server.
set -euo pipefail
curl -s http://localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "llm",
  "messages": [{"role": "user", "content": "Explain a GPU to a 10-year-old in two sentences."}]
}' | python3 -m json.tool
