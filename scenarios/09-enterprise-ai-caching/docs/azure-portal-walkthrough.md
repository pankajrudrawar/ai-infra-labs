# Part A: Build the Azure side in the portal

You build a private Azure Managed Redis cache with vector search, sign in with a managed
identity (no passwords), run the demo app from a small VM inside the network, then add a
second region and test active-active replication.

**Time:** about 90 minutes, most of it waiting for the cache to deploy.
**Cost:** about $0.24/hour, $0.40/hour once the second region exists. Delete everything at the end (step 12).
**Names used below:** prefix `hp-aicache`, region **East US 2**, second region **West US 3**.
Cache names must be unique across Azure, so add your initials (for example `hp-aicache-pr-primary`).

> Portal labels change from time to time. If a label below doesn't match, look for the
> setting by name; the values are what matter.

## 0. Before you start (once)

1. **Budget alert.** Portal search bar → **Cost Management** → **Budgets** → **+ Add**.
   Scope: your lab subscription. Amount: `$20` monthly. Alert at 50%, 80%, 100% to your email.
2. **Register the resource provider.** **Subscriptions** → your subscription →
   **Resource providers** → search `Microsoft.Cache` → **Register** (if it isn't already).
3. **SSH key.** On your laptop, if you don't have one: `ssh-keygen -t ed25519`. You'll
   paste the *public* key (`~/.ssh/id_ed25519.pub`) and upload the *private* key in Bastion.

## 1. Resource group

**Resource groups** → **+ Create** → Name `rg-hp-aicache`, Region **East US 2** →
**Tags** tab: `project = ai-infra-series`, `scenario = 09` → **Review + create** → **Create**.

Use these two tags on every resource below.

## 2. Network

1. **Virtual networks** → **+ Create**.
   - Basics: resource group `rg-hp-aicache`, name `vnet-hp-aicache-primary`, region East US 2.
   - IP addresses: address space `10.90.0.0/16`. Delete the default subnet and add two:
     - `snet-app` → `10.90.1.0/24` (the VM)
     - `snet-private-endpoints` → `10.90.2.0/24` (the cache's private IP)
   - **Review + create** → **Create**.
2. **NAT gateway** (gives the VM outbound internet for `pip install`, with no public IP on the VM):
   **NAT gateways** → **+ Create** → name `nat-hp-aicache`, region East US 2 →
   **Outbound IP**: **Create a new public IP address** `pip-hp-aicache-nat` →
   **Networking/Subnet** tab: VNet `vnet-hp-aicache-primary`, tick `snet-app` → **Create**.

> **What's a private endpoint?** A private IP address inside *your* network that leads to
> a managed service. Apps reach the cache through it; the internet can't reach it at all.

## 3. Managed identity for the app

**Managed Identities** → **+ Create** → resource group `rg-hp-aicache`, region East US 2,
name `id-hp-aicache-app` → **Create**.

> **What's a managed identity?** An identity Azure creates and rotates for you. The VM
> asks Azure for a short-lived token and uses it to sign in to the cache. There is no
> password anywhere to leak.

## 4. Create the Azure Managed Redis cache

Portal search bar → **Azure Managed Redis** → **+ Create**.

**Basics**
- Resource group `rg-hp-aicache`, DNS name `hp-aicache-<initials>-primary`, region **East US 2**.
- Performance tier: **Balanced (for general purpose workloads)**.
- Cache size: **B3 (3 GB)**. B3 is the smallest size that supports geo-replication.
  (Production design: B20.)

**Networking**
- Connectivity method: **Private endpoint** → **+ Add**:
  - Name `pe-hp-aicache-primary`, subresource `redisEnterprise`.
  - Virtual network `vnet-hp-aicache-primary`, subnet `snet-private-endpoints`.
  - Integrate with private DNS zone: **Yes** (creates `privatelink.redis.azure.net`).

**Active geo-replication**
- **Enable**, group name `hp-aicache-geo`.
  The cache starts as a group of one. Adding geo-replication later means recreating the
  database and losing its data, so production caches turn it on from day one.

**Advanced**
- **Modules:** tick **RediSearch** (vector search). The portal then sets the clustering
  policy to **Enterprise** and eviction to **NoEviction**, which RediSearch requires.
- **High availability:** **Enabled**.
- **Authentication:** **Microsoft Entra authentication** enabled;
  **Access keys authentication: Disabled**.
- **Non-TLS access:** off. **Data persistence:** disabled (it's a cache).

**Tags** → add both tags → **Review + create** → **Create**.

Deployment takes about 10–20 minutes. Carry on with step 5 meanwhile.

> **Why NoEviction matters:** normally a full cache throws out old keys to make room. With
> NoEviction it refuses new writes instead. That is why every key the app writes has a TTL
> (time to live), why the app skips caching when a write fails, and why step 9 sets an
> alert at 75% memory.

## 5. Test VM (no public IP)

**Virtual machines** → **+ Create** → **Azure virtual machine**.

- **Basics:** resource group `rg-hp-aicache`, name `vm-hp-aicache`, region East US 2,
  image **Ubuntu Server 24.04 LTS**, size **Standard_B2s**, authentication **SSH public key**,
  username `azureuser`, key source **Use existing public key** → paste your public key.
  Public inbound ports: **None**.
- **Disks:** Standard SSD is plenty.
- **Networking:** VNet `vnet-hp-aicache-primary`, subnet `snet-app`,
  **Public IP: None**.
- **Management:** Identity → **User assigned** → add `id-hp-aicache-app`.
- **Advanced → Custom data:** paste this (installs Python and clones this repo on first boot):

  ```yaml
  #cloud-config
  package_update: true
  packages: [python3-venv, git, redis-tools]
  runcmd:
    - git clone https://github.com/pankajrudrawar/ai-infra-labs.git /opt/ai-infra-labs
    - python3 -m venv /opt/venv
    - /opt/venv/bin/pip install -r /opt/ai-infra-labs/scenarios/09-enterprise-ai-caching/app/requirements.txt
    - chown -R azureuser /opt/ai-infra-labs /opt/venv
  ```
- **Tags** → **Review + create** → **Create**.

## 6. Let the app identity into the cache

When the cache shows **Running**: open it → **Settings → Authentication** →
**Microsoft Entra Authentication** tab → **Select member** (or **+ Add**) →
choose the managed identity **`id-hp-aicache-app`** → **Save**.

This gives the identity the default data access policy on the cache's database.

While you're on the cache, note from **Overview**: **Host name**
(`hp-aicache-<initials>-primary.eastus2.redis.azure.net`) and port **10000**.

## 7. Connect to the VM with Bastion Developer (free)

VM → **Connect** → **Connect via Bastion** → **Deploy Bastion Developer** (the free tier,
deploys in a minute or two) → authentication **SSH Private Key from Local File** →
username `azureuser`, upload your private key → **Connect**. A terminal opens in the browser.

Check the private DNS works and the cache answers:

```bash
nslookup hp-aicache-<initials>-primary.eastus2.redis.azure.net   # expect a 10.90.2.x address
cloud-init status --wait                                          # wait for pip to finish
source /opt/venv/bin/activate && cd /opt/ai-infra-labs/scenarios/09-enterprise-ai-caching/app

export CACHE_HOST=hp-aicache-<initials>-primary.eastus2.redis.azure.net
export CACHE_PORT=10000 CACHE_TLS=1 CACHE_CLUSTER=0 CACHE_AUTH=entra
export AZURE_CLIENT_ID=<client ID of id-hp-aicache-app, from its Overview page>
python3 cache_client.py          # PING ok in ~1 ms
```

## 8. Run the demo

```bash
python3 demo.py --sweep          # choose a threshold: paraphrases served vs. traps served
export CACHE_THRESHOLD=<value from the sweep>
python3 demo.py --no-cache -n 60 # baseline: every request waits for the (mock) LLM
python3 demo.py -n 300           # with the cache: watch the hit rate climb
python3 demo.py --traps          # near-miss questions must say "ok: sent to LLM"
python3 patterns_demo.py         # chat memory, token budget, feature reads in ms
```

The default LLM is a mock that waits 1.2–2.5 s, so the lab costs nothing. To use a real
model, set `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL` for any OpenAI-compatible endpoint
(Azure OpenAI's v1 endpoint, or the vLLM server from Scenario 01).

Look inside the cache:

```bash
python3 -c "
from cache_client import connect
r = connect(decode_responses=True)
info = r.execute_command('FT.INFO', 'llmcache_idx')
print(dict(zip(info[::2], info[1::2])).get('num_docs'), 'cached answers')
print(r.info('memory')['used_memory_human'], 'used')
for k in list(r.scan_iter('llmcache:v:*', count=100))[:3]:
    print(k, '->', r.hget(k, 'prompt'), '| TTL', r.ttl(k), 's')
"
```

## 9. Watch it in the portal

Cache → **Monitoring → Metrics**. Add charts for **Used Memory Percentage**, **Cache Hits**,
**Cache Misses**, **Connected Clients** and **Server Load**. Run `demo.py -n 300` again and
record the charts for the video.

**Alerts → + Create → Alert rule:** Used Memory Percentage greater than 75% for 5 minutes,
action group = email you. In production add Server Load > 80% and a geo-replication health alert.

## 10. Add a second region (active-active)

1. Create a second cache exactly like step 4, but: name `hp-aicache-<initials>-secondary`,
   region **West US 3**, and on **Active geo-replication** choose **link to the existing
   group** `hp-aicache-geo` / the primary cache. Same tier, size, modules.
2. **Private endpoint:** for the lab, put it in the *same* VNet as the VM
   (`vnet-hp-aicache-primary`, subnet `snet-private-endpoints`). A private endpoint can sit
   in a different region from its cache, so the VM reaches both without extra networking.
   (Production gives each region its own VNet; the Terraform does that, with peering.)
3. Repeat step 6 on the new cache for `id-hp-aicache-app`.
4. On the VM:

   ```bash
   READ_HOST=hp-aicache-<initials>-secondary.westus3.redis.azure.net python3 replication_check.py
   ```

   It writes in East US 2 and times how long until West US 3 sees it. Swap the two hosts
   to show writes work in both directions (that's "active-active").

**Failover drill:** point `CACHE_HOST` at the West US 3 cache and run `demo.py -n 100`.
The hit rate is high straight away, because the cached answers already replicated.

## 11. Optional: see fail-open in action

Set `CACHE_HOST` to a wrong name and run `demo.py -n 20`. Every request still gets an
answer (from the LLM), and the summary shows `cache errors`. That's the behavior you want
when a cache has an outage.

## 12. Tear down

**Resource groups** → `rg-hp-aicache` → **Delete resource group** → type the name → **Delete**.
That removes the caches, VM, NAT gateway, Bastion Developer, private endpoints and DNS zone.
Cache deletion takes several minutes. Next day, check **Cost Management → Cost analysis**
filtered by tag `scenario = 09`.

Next: [Part B, Google Cloud](gcp-console-walkthrough.md) · [Automation](automation.md)
