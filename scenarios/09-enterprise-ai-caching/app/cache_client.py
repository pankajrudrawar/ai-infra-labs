"""One connection factory for Azure Managed Redis and Google Memorystore for Valkey.

Everything is configured with environment variables, so the same code runs on both clouds:

  CACHE_HOST      hostname or IP of the cache endpoint (Memorystore: the discovery endpoint)
  CACHE_PORT      10000 for Azure Managed Redis, 6379 for Memorystore
  CACHE_TLS       1 (default) or 0
  CACHE_CA_FILE   path to the server CA PEM (Memorystore with in-transit encryption)
  CACHE_CLUSTER   1 for Memorystore cluster mode, 0 for Azure Managed Redis (Enterprise policy)
  CACHE_AUTH      entra | gcp-iam | password | none
  CACHE_PASSWORD  only for CACHE_AUTH=password (access key, kept out of source control)

entra   : Microsoft Entra ID token from the VM's managed identity (needs `redis-entraid`).
gcp-iam : Google access token of the VM's service account, refreshed automatically
          (needs `google-auth`; the account needs roles/memorystore.dbConnectionUser).
"""
import os
import threading
import time

import redis
from redis.credentials import CredentialProvider


class GoogleIamCredentialProvider(CredentialProvider):
    """Sends a fresh Google OAuth access token as the AUTH password (username 'default')."""

    def __init__(self):
        import google.auth
        from google.auth.transport.requests import Request

        self._creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        self._request = Request()
        self._lock = threading.Lock()

    def get_credentials(self):
        with self._lock:
            # Tokens last one hour; refresh when less than five minutes remain.
            expiry = getattr(self._creds, "expiry", None)
            if not self._creds.valid or (expiry and expiry.timestamp() - time.time() < 300):
                self._creds.refresh(self._request)
            return (self._creds.token,)


def _credential_kwargs():
    mode = os.environ.get("CACHE_AUTH", "none").lower()
    if mode == "entra":
        from redis_entraid.cred_provider import create_from_default_azure_credential

        provider = create_from_default_azure_credential(("https://redis.azure.com/.default",))
        return {"credential_provider": provider}
    if mode == "gcp-iam":
        return {"credential_provider": GoogleIamCredentialProvider()}
    if mode == "password":
        return {"password": os.environ["CACHE_PASSWORD"]}
    return {}


def connect(decode_responses=False):
    host = os.environ["CACHE_HOST"]
    port = int(os.environ.get("CACHE_PORT", "6379"))
    tls = os.environ.get("CACHE_TLS", "1") == "1"
    kwargs = dict(
        host=host,
        port=port,
        decode_responses=decode_responses,
        protocol=2,                  # RESP2 replies look the same on Redis and Valkey
        socket_timeout=2,            # a cache must never be slower than the thing it protects
        socket_connect_timeout=2,
        health_check_interval=30,
        **_credential_kwargs(),
    )
    if tls:
        kwargs["ssl"] = True
        ca = os.environ.get("CACHE_CA_FILE")
        if ca:
            kwargs["ssl_ca_certs"] = ca
    if os.environ.get("CACHE_CLUSTER", "0") == "1":
        return redis.RedisCluster(**kwargs)
    return redis.Redis(**kwargs)


if __name__ == "__main__":
    r = connect(decode_responses=True)
    t = time.perf_counter()
    r.ping()
    print(f"PING ok in {(time.perf_counter() - t) * 1000:.1f} ms")
    info = r.info("server")
    if isinstance(info, dict) and "redis_version" not in info:   # cluster: one dict per node
        info = next(iter(info.values()))
    print("server:", info.get("redis_version"), info.get("valkey_version", ""))
