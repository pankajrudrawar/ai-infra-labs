# Video plan: Episode 9

**Working title:** "We cut our AI bill by caching answers: an enterprise cache on Azure and Google Cloud"
**Alt titles:** "Semantic caching for LLMs, built for real" · "Azure Managed Redis vs. Google Valkey for AI"
**Length:** about 25 minutes, or two parts (Part 1: design + Azure, Part 2: Google + automation).
**Thumbnail:** the two cache boxes from the diagram, a big "−30% LLM calls", the Azure and Google Cloud logos.

## Opening (the series format)

| Time | On screen | Say |
| --- | --- | --- |
| 0:00 | Bill chart climbing to $180k | "This company pays $180,000 a month for AI answers. Forty percent are the same questions asked differently." |
| 0:25 | Title card | Episode 9, enterprise track. |
| 0:40 | **Architecture diagram** (`architecture-diagram.png`), built up box by box | Walk left to right: users → app → cache → LLM, then the second region, then the pipeline. |
| 2:30 | **Plan summary** card | "Today: design it, size it, secure it, build it by hand on both clouds, then automate it. Budget: under $5." |

Plan summary card:
- Two AI apps, two clouds, one caching design
- Azure Managed Redis (active-active, two regions) and Memorystore for Valkey (cross-region standby)
- Private only, no passwords, TLS
- Same Python app on both clouds
- Terraform + GitHub Actions to rebuild it in one command
- Measure: hit rate, latency, dollars saved

## Beginner glossary (one card each, about 20 seconds)

| Term | Plain English |
| --- | --- |
| **Cache** | A fast notepad in memory. Check it before doing slow, expensive work. |
| **Cache hit / miss** | Hit: the answer was in the notepad. Miss: it wasn't, so do the work and write it down. |
| **TTL (time to live)** | An expiry date on each note, so old answers disappear by themselves. |
| **Eviction** | What the cache does when it's full: throw out old notes (or, with NoEviction, refuse new ones). |
| **Redis / Valkey** | The most popular in-memory databases. Valkey is the open-source fork of Redis; they speak the same language. |
| **LLM (large language model)** | The AI that writes answers, like GPT or Gemini. Each answer costs money and takes seconds. |
| **Token** | A piece of a word. LLMs are priced and rate-limited per token. |
| **Embedding** | A list of numbers that captures what a sentence *means*. Similar meanings get similar numbers. |
| **Vector search** | Finding the stored embeddings closest to a new one: "which question we've seen is most like this one?" |
| **Semantic cache** | A cache that matches by meaning instead of exact words, using vector search. |
| **Cosine distance / threshold** | How far apart two meanings are (0 = same). The threshold is how close is close enough to reuse an answer. |
| **Feature store (online features)** | Pre-computed facts about each customer that a model reads in milliseconds. |
| **Replica / high availability** | A live copy in another data center that takes over if the first one fails. |
| **Shard** | One slice of the data. More shards = more memory and throughput. |
| **Geo-replication (active-active vs. active-passive)** | Copies in other regions. Active-active: write anywhere. Active-passive: one writer, standby copies. |
| **Private endpoint / Private Service Connect** | A private address in your own network for a cloud service, invisible from the internet. |
| **Managed identity / IAM auth** | The app proves who it is with short-lived tokens from the cloud, not passwords. |
| **Terraform (IaC)** | Infrastructure written as code, so you can review it, repeat it and delete it cleanly. |
| **CI / OIDC** | Automatic checks on every change; OIDC lets GitHub sign in to clouds without stored keys. |

## Story beats

1. **Design (5 min):** the four jobs of the cache; why one cache per cloud; decision tables;
   sizing on screen with `cache_sizing.py` ("embedding size is the biggest lever").
2. **Azure build (6 min):** portal, fast-cut: VNet, cache with RediSearch + Entra + geo group,
   managed identity, Bastion Developer. Highlight the NoEviction warning.
3. **The money shot (3 min):** `demo.py --no-cache` vs. `demo.py -n 300`, side by side.
   Then `--sweep` and `--traps`: "Ridgeline 2 vs. Ridgeline 4: a cache that's too eager gives
   the wrong answer. Here's how we pick the threshold."
4. **Google build (4 min):** same steps, call out the differences: shards, PSC, IAM token,
   CA file. Same app, only env vars change.
5. **Second region + failover (3 min):** `replication_check.py` on both; Azure write-anywhere
   vs. Google switchover.
6. **Automation (3 min):** `terraform plan` output, the GitHub Actions run, "a human reads
   the plan before apply".
7. **Cost + verdict (1.5 min):** the cost table; $3.6k/month cache vs. $54k/month saved;
   comparison table and when to pick which.
8. **Teardown + next (30 s).**

## Shot list / screen recordings

- [ ] Diagram build-up (export frames from `video/architecture.html` as for Scenario 01)
- [ ] Azure: Advanced tab with RediSearch, NoEviction, Entra auth
- [ ] Azure metrics: Cache Hits climbing during the demo
- [ ] Terminal: sweep table, with/without cache results, traps
- [ ] Google: Create instance form, IAM auth + in-transit encryption
- [ ] Google: secondary instance + switchover
- [ ] GitHub Actions run, green checks + Checkov report
- [ ] Cost analysis filtered by `scenario = 09` the day after

## Description and chapters

Copy the chapter times after editing. Link the repo folder, the Medium post, and the
pricing pages. Add the disclaimer: "Harbor & Pine is a fictional company; numbers are illustrative."
