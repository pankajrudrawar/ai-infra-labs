#!/usr/bin/env python3
"""The three other caching jobs in the Harbor & Pine design, each in a few lines.

  1. Chat memory   : last N messages of a conversation, expires when the chat goes idle.
  2. Token budget  : per-tenant LLM token limit per minute, shared by every app instance.
  3. Online features: the recommendation model reads customer features in about a millisecond.

  python3 patterns_demo.py
"""
import json
import random
import time

from cache_client import connect

r = connect(decode_responses=True)


# 1. Chat memory -----------------------------------------------------------------
def remember(session_id, role, text, keep=20, idle_ttl=1800):
    key = f"chat:{{{session_id}}}:history"          # {..} keeps a session's keys on one shard
    pipe = r.pipeline(transaction=False)
    pipe.rpush(key, json.dumps({"role": role, "text": text, "ts": int(time.time())}))
    pipe.ltrim(key, -keep, -1)
    pipe.expire(key, idle_ttl)
    pipe.execute()


def history(session_id):
    return [json.loads(m) for m in r.lrange(f"chat:{{{session_id}}}:history", 0, -1)]


# 2. Token budget ------------------------------------------------------------------
def spend_tokens(tenant, tokens, limit_per_minute=50_000):
    """Fixed one-minute window. Returns True if the call is allowed."""
    key = f"budget:{tenant}:{int(time.time() // 60)}"
    pipe = r.pipeline(transaction=False)
    pipe.incrby(key, tokens)
    pipe.expire(key, 120)
    used, _ = pipe.execute()
    return used <= limit_per_minute


# 3. Online features ----------------------------------------------------------------
def load_features(n=2000):
    pipe = r.pipeline(transaction=False)
    for i in range(n):
        pipe.hset(f"feat:cust:{i}", mapping={
            "lifetime_value": round(random.uniform(20, 4000), 2),
            "orders_90d": random.randint(0, 12),
            "fav_category": random.choice(["tents", "boots", "jackets", "packs"]),
            "churn_risk": round(random.random(), 3),
        })
        pipe.expire(f"feat:cust:{i}", 7 * 24 * 3600)
    pipe.execute()


if __name__ == "__main__":
    remember("s-123", "user", "Do you ship to Canada?")
    remember("s-123", "assistant", "Yes, 5-8 business days.")
    print("1. chat memory     :", history("s-123"))

    allowed = [spend_tokens("tenant-a", 12_000) for _ in range(6)]
    print("2. token budget    :", allowed, "(the 5th call goes over 50k tokens/minute)")

    load_features()
    lat = []
    for _ in range(500):
        t = time.perf_counter()
        r.hgetall(f"feat:cust:{random.randrange(2000)}")
        lat.append((time.perf_counter() - t) * 1000)
    lat.sort()
    print(f"3. feature lookups : p50 {lat[249]:.2f} ms, p99 {lat[494]:.2f} ms over 500 reads")
