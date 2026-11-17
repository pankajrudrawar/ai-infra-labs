"""The 'expensive thing' the cache protects.

Default: a mock LLM that waits like a real one and charges a pretend price, so the lab
costs nothing and needs no API key.

Optional: any OpenAI-compatible chat endpoint (Azure OpenAI v1 endpoint, Vertex AI's
OpenAI-compatible endpoint, or the vLLM server from Scenario 01):
  LLM_BASE_URL=https://.../v1  LLM_API_KEY=...  LLM_MODEL=...
"""
import os
import random
import time

import requests

PRICE_PER_CALL = float(os.environ.get("LLM_PRICE_PER_CALL", "0.004"))   # USD, illustrative


class MockLLM:
    name = "mock"

    def __call__(self, prompt):
        time.sleep(random.uniform(1.2, 2.5))        # typical time for a ~300-token answer
        return f"[answer generated for: {prompt.strip()}]"


class OpenAICompatibleLLM:
    def __init__(self):
        self.url = os.environ["LLM_BASE_URL"].rstrip("/") + "/chat/completions"
        self.key = os.environ.get("LLM_API_KEY", "")
        self.name = os.environ.get("LLM_MODEL", "default")

    def __call__(self, prompt):
        r = requests.post(self.url, timeout=60, headers={"Authorization": f"Bearer {self.key}",
                                                         "api-key": self.key},
                          json={"model": self.name, "max_tokens": 300,
                                "messages": [{"role": "system", "content": "You are a helpful retail support assistant."},
                                             {"role": "user", "content": prompt}]})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def get_llm():
    return OpenAICompatibleLLM() if os.environ.get("LLM_BASE_URL") else MockLLM()
