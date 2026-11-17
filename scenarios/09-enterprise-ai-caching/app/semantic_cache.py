"""A two-level LLM response cache that works on Azure Managed Redis (RediSearch module)
and Google Memorystore for Valkey (built-in vector search).

Level 1, exact match : SHA-256 of the normalised prompt -> cached answer. Cheap and safe.
Level 2, semantic    : nearest stored question by meaning (vector KNN). If it is closer than
                       the threshold, reuse its answer. This is what catches paraphrases.

Design rules that matter in production:
  * Fail open. If the cache is down or full, the user still gets an answer from the LLM.
  * Scope every lookup (tenant + model + prompt version), so one customer's answer or an
    old prompt template is never served to someone else.
  * Every key has a TTL. Azure Managed Redis with RediSearch runs with NoEviction, so
    TTLs are the only thing that frees memory.
  * Only cache answers that are safe to share: no personal data, no account-specific facts.
"""
import hashlib
import logging
import re
import time

import numpy as np
import redis

log = logging.getLogger("semantic_cache")


def _norm(text):
    return re.sub(r"\s+", " ", text.strip().lower())


def _scope(*parts):
    # TAG values with punctuation need escaping; keep them to [A-Za-z0-9_].
    return re.sub(r"[^A-Za-z0-9_]", "_", "_".join(parts))


class SemanticCache:
    def __init__(self, client, embedder, index="llmcache_idx", prefix="llmcache:",
                 threshold=0.10, ttl_seconds=24 * 3600):
        self.r = client
        self.embed = embedder
        self.index = index
        self.prefix = prefix
        self.threshold = threshold          # cosine distance: 0 = identical meaning, 2 = opposite
        self.ttl = ttl_seconds
        self.stats = {"exact": 0, "semantic": 0, "miss": 0, "errors": 0}

    # ---------- setup ----------
    def ensure_index(self):
        try:
            self.r.execute_command("FT.INFO", self.index)
            return False
        except redis.ResponseError:
            pass
        self.r.execute_command(
            "FT.CREATE", self.index, "ON", "HASH", "PREFIX", "1", self.prefix + "v:",
            "SCHEMA",
            "embedding", "VECTOR", "HNSW", "6", "TYPE", "FLOAT32", "DIM", str(self.embed.dim),
            "DISTANCE_METRIC", "COSINE",
            "scope", "TAG",
        )
        return True

    # ---------- read path ----------
    def lookup(self, prompt, tenant="public", model="default", prompt_version="v1"):
        """Return (answer, kind, distance). kind is 'exact', 'semantic' or 'miss'."""
        scope = _scope(tenant, model, prompt_version)
        exact_key = f"{self.prefix}x:{scope}:{hashlib.sha256(_norm(prompt).encode()).hexdigest()}"
        try:
            hit = self.r.get(exact_key)
            if hit is not None:
                self.stats["exact"] += 1
                return hit.decode(), "exact", 0.0

            vec = self.embed(prompt)
            res = self.r.execute_command(
                "FT.SEARCH", self.index,
                f"@scope:{{{scope}}}=>[KNN 1 @embedding $vec AS dist]",
                "PARAMS", "2", "vec", vec.tobytes(),
                "DIALECT", "2",
            )
            if res and res[0] > 0:
                key = res[1]
                fields = dict(zip(res[2][::2], res[2][1::2], strict=False)) if len(res) > 2 else {}
                # Recompute the distance from the stored vector instead of trusting the
                # engine's score field: its name and precision differ between engines
                # (a local valkey-search 8.1 build returned it rounded to whole numbers).
                raw = fields.get(b"embedding") or self.r.hget(key, "embedding")
                dist = 1.0 - float(np.dot(np.frombuffer(raw, dtype=np.float32), vec))
                if dist <= self.threshold:
                    answer = fields.get(b"response") or self.r.hget(key, "response")
                    if answer is not None:
                        self.stats["semantic"] += 1
                        return answer.decode(), "semantic", dist
                self.stats["miss"] += 1
                return None, "miss", dist
        except (redis.RedisError, OSError) as e:      # fail open
            self.stats["errors"] += 1
            log.warning("cache lookup failed, falling back to LLM: %s", e)
        self.stats["miss"] += 1
        return None, "miss", None

    # ---------- write path ----------
    def store(self, prompt, answer, tenant="public", model="default", prompt_version="v1", vec=None):
        scope = _scope(tenant, model, prompt_version)
        digest = hashlib.sha256(_norm(prompt).encode()).hexdigest()
        exact_key = f"{self.prefix}x:{scope}:{digest}"
        vec_key = f"{self.prefix}v:{scope}:{digest}"
        vec = self.embed(prompt) if vec is None else vec
        try:
            # Not a MULTI/EXEC transaction: the two keys can live on different cluster shards.
            pipe = self.r.pipeline(transaction=False)
            pipe.hset(vec_key, mapping={
                "embedding": vec.tobytes(), "response": answer, "prompt": prompt,
                "scope": scope, "created": int(time.time()),
            })
            pipe.expire(vec_key, self.ttl)
            pipe.set(exact_key, answer, ex=self.ttl)
            pipe.execute()
        except (redis.RedisError, OSError) as e:      # e.g. OOM under NoEviction: skip caching
            self.stats["errors"] += 1
            log.warning("cache store skipped: %s", e)


class Embedder:
    """Small local embedding model (no API key, no cost). 384 dimensions."""

    def __init__(self, model_name="BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding

        self._m = TextEmbedding(model_name)
        self.dim = len(self(" "))

    def __call__(self, text):
        v = np.asarray(next(iter(self._m.embed([text]))), dtype=np.float32)
        return v / np.linalg.norm(v)
