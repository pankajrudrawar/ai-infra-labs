#!/usr/bin/env python3
"""Napkin-math GPU memory sizing for LLM inference.

Example:
    python3 sizing.py --params 8 --layers 32 --kv-heads 8 --head-dim 128 --gpu-gb 24
    python3 sizing.py --params 8 --layers 32 --kv-heads 8 --head-dim 128 --gpu-gb 24 --bits 4
"""
import argparse

GB = 1e9


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--params", type=float, required=True, help="model size in billions of parameters")
    p.add_argument("--layers", type=int, required=True, help="number of transformer layers")
    p.add_argument("--kv-heads", type=int, required=True, help="number of key/value heads (GQA)")
    p.add_argument("--head-dim", type=int, required=True, help="dimension per attention head")
    p.add_argument("--gpu-gb", type=float, required=True, help="GPU memory in GB")
    p.add_argument("--bits", type=int, default=16, help="weight precision in bits (16, 8, 4)")
    p.add_argument("--kv-bytes", type=int, default=2, help="bytes per KV-cache value (2 = FP16/BF16)")
    p.add_argument("--util", type=float, default=0.90, help="fraction of GPU memory vLLM may use")
    p.add_argument("--overhead-gb", type=float, default=1.5, help="activations, CUDA graphs, runtime")
    p.add_argument("--context", type=int, default=8192, help="tokens per long conversation")
    a = p.parse_args()

    weights = a.params * 1e9 * a.bits / 8 / GB
    kv_per_token = 2 * a.layers * a.kv_heads * a.head_dim * a.kv_bytes  # bytes (K and V)
    usable = a.gpu_gb * a.util
    kv_budget = usable - weights - a.overhead_gb

    print(f"Weights            : {weights:6.1f} GB  ({a.params}B params x {a.bits}-bit)")
    print(f"KV cache per token : {kv_per_token / 1024:6.0f} KB")
    print(f"Per {a.context:,}-token chat : {kv_per_token * a.context / GB:6.2f} GB")
    print(f"Usable GPU memory  : {usable:6.1f} GB  ({a.gpu_gb} GB x {a.util:.0%})")
    if kv_budget <= 0:
        print(f"Does NOT fit: short by {-kv_budget:.1f} GB. Use a bigger GPU or fewer bits.")
        return
    tokens = kv_budget * GB / kv_per_token
    print(f"Left for KV cache  : {kv_budget:6.1f} GB  -> about {tokens:,.0f} tokens")
    print(f"Long chats at once : {tokens / a.context:6.1f}")


if __name__ == "__main__":
    main()
