# Azure Managed Redis vs. Google Cloud Memorystore for Valkey

As built in this scenario, November 2026. Both change quickly; check current docs.

| | Azure Managed Redis | Memorystore for Valkey |
| --- | --- | --- |
| Engine | Redis Enterprise software, run by Microsoft (co-engineered with Redis) | Valkey, the open-source (Linux Foundation) fork of Redis |
| Protocol | Redis (RESP2/RESP3), port 10000, TLS | Redis-compatible (RESP), port 6379, TLS optional |
| How you size it | Pick a tier and SKU: Memory Optimized, **Balanced**, Compute Optimized, Flash Optimized; B0 (0.5 GB) to B1000 | Pick a node type (shared-core-nano 1.4 GB to highmem-2xlarge 110 GB) × shards × replicas |
| Scale-out | Inside the SKU (multiple Redis processes per node); move to a bigger SKU to grow | Add shards (cluster mode) or replicas; online |
| Cluster modes | Enterprise (one endpoint), OSS cluster (cluster-aware clients), non-clustered | Cluster mode enabled (discovery endpoint) or disabled (primary + reader endpoints) |
| Vector search | **RediSearch** module (choose at creation); HASH and JSON; also full-text search | **Built in**; HASH; vector + TAG + NUMERIC filters (check current docs for full-text and JSON support) |
| Other modules | RedisJSON, RedisBloom, RedisTimeSeries | None (core Valkey data types) |
| High availability | Toggle per cache: replica in another zone | Replicas per shard (0–5), multi-zone placement |
| Multi-region | **Active-active** geo-replication, up to 5 regions, every region writable (CRDTs), B3 and up | **Active-passive** cross-region replication: one primary, read-only secondaries, switchover/detach to fail over |
| Persistence | RDB or AOF (not with geo-replication) | RDB snapshots or AOF |
| Eviction with vector search | Must be NoEviction; rely on TTLs | Normal policies (`volatile-lru` etc.) |
| Private access | Private endpoint + private DNS | Private Service Connect via service connection policy |
| Passwordless sign-in | Microsoft Entra ID (managed identities), access keys can be disabled | IAM auth (`roles/memorystore.dbConnectionUser`), 1-hour tokens |
| Encryption at rest | On; customer-managed keys optional | On; CMEK optional |
| Terraform | `azurerm_managed_redis`, `_geo_replication`, `_access_policy_assignment` | `google_memorystore_instance` |
| Price shape | Per SKU-hour; HA doubles it (B20 with HA ≈ $918/month in East US 2) | Per node-hour, every shard and replica counts (highmem-medium $0.1923/h in us-central1) |
| Discounts | 1- and 3-year reservations | Committed use: 20% (1 year), 40% (3 years) |

## When to pick which

- **Write traffic in several regions at once** (users everywhere, global sessions):
  Azure Managed Redis active-active is the simpler answer.
- **Large, growing datasets that need to scale out** (features for tens of millions of
  users): Memorystore's shard-based model grows in small steps.
- **Need JSON documents, full-text search, Bloom filters or time series in the cache:** Azure
  Managed Redis, because of its modules.
- **Want a fully open-source engine** with no license questions: Valkey.
- **Already on one cloud:** use that cloud's service next to your compute. A cache that is
  one network hop away beats a better cache in another cloud.

## Gotchas found while designing this

- Azure: RediSearch forces NoEviction. A full cache rejects writes, so TTLs, memory alerts
  and fail-open code are not optional.
- Azure: the geo-replication group, clustering policy and modules are set at creation.
  Changing them later recreates the database.
- Google: cluster mode needs a cluster-aware client. Keys used together (one chat session)
  need a hash tag like `chat:{session-id}:history` to stay on one shard.
- Google: IAM tokens expire hourly. Use a credential provider that refreshes them, not a
  token pasted into an environment variable.
- Both: vectors are stored twice (in the key and in the index), so budget twice the raw
  vector size.
- Engine differences: the KNN score field differed between engines in local tests, so the
  demo computes the distance itself.
