# Medium post outline

**Title:** How We'd Cut an AI Bill by 30% With a Cache: Azure Managed Redis and Google Memorystore, Designed and Automated
**Subtitle:** A real-world enterprise design for semantic LLM caching, chat memory and online features on two clouds, with Terraform and CI.
**Tags:** AI Infrastructure, Redis, Google Cloud, Azure, LLM
**Reading time target:** 12–14 minutes. Cover image: `architecture-diagram.png`.

## 1. The problem (hook)
- Harbor & Pine (fictional): $180k/month LLM bill, 40% repeated questions, slow answers,
  Black Friday rate limits, a recommendation model missing its latency budget.
- One line: "The cheapest LLM call is the one you don't make."

## 2. What a cache does for AI (for beginners)
- Cache, hit/miss, TTL, eviction in two paragraphs.
- Embeddings and vector search with one picture: questions as points, close points mean the same thing.
- Exact cache vs. semantic cache.

## 3. The architecture
- Diagram. Why one cache per cloud, next to the compute.
- The four jobs: semantic cache, chat memory, token budgets, online features.

## 4. Design decisions (the architect's section)
- Azure table: Balanced B20, RediSearch, Enterprise cluster, NoEviction, HA, active-active, Entra only, private endpoint.
- Google table: cluster mode, 3 × highmem-medium + replicas, multi-zone, IAM auth, PSC, cross-region standby.
- Callout: things you can't change later (geo group, modules, clustering policy, TLS mode).

## 5. Sizing with real math
- Per-entry formula; vectors stored twice; embedding dimensions as the biggest lever (1,536 → 512 = 23 GB → 12 GB).
- Script output screenshots for both clouds.

## 6. Making a semantic cache safe
- Scope keys (tenant, model, prompt version); only cache shareable answers.
- The threshold sweep table and the trap questions (Ridgeline 2 vs. 4).
- Fail open, with the code snippet from `semantic_cache.py`.

## 7. Building it (condensed)
- Azure portal highlights, Google console highlights; link the full walkthroughs in the repo.
- Results table from the lab: hit rate, p50/p95 with and without cache, LLM spend, feature read p99, replication lag.

## 8. High availability and disaster recovery
- Failure table (node, zone, region, total outage). RPO/RTO in plain words.
- Active-active vs. active-passive: what that means for your failover runbook.

## 9. Security checklist
- No public endpoints, no passwords, TLS, least privilege, no personal data in the semantic cache, OIDC in CI.

## 10. Automation
- Terraform structure, the variables that switch lab → production.
- The GitHub Actions pipeline: fmt/validate/tflint/Checkov on every PR, manual plan with OIDC, a human approves apply.

## 11. Cost and ROI
- Production table (≈ $3.6k/month) vs. ≈ $54k/month saved at a 30% hit rate.
- Lab cost (under $5) and the teardown habit.

## 12. Azure vs. Google: which would I pick?
- Short version of `comparison.md` and the "when to pick which" list.

## 13. Wrap-up
- Three takeaways: size by embedding dimensions, pick the threshold with data, fail open.
- Link to the repo, the video, and the next episode.
