# Part B: Build the Google Cloud side in the console

You build a private Memorystore for Valkey instance (cluster mode, vector search, IAM sign-in,
TLS), run the **same** demo app from a VM in the VPC, then add a read-only secondary in a
second region and practice a failover.

**Time:** about 60 minutes. **Cost:** about $0.08/hour, $0.12/hour with the secondary.
Delete everything at the end (step 11).
**Names used below:** prefix `hp-aicache`, region **us-central1**, second region **us-east4**.

> Console labels change from time to time. If a label below doesn't match, look for the
> setting by name; the values are what matter.

## 0. Before you start (once)

1. **A project just for labs** (top bar project picker → **New project**), linked to billing.
2. **Budget alert:** **Billing** → **Budgets & alerts** → **Create budget** → this project,
   `$20`/month, alerts at 50/80/100%.
3. **Enable APIs:** **APIs & Services** → **Library**, enable each of:
   **Memorystore API**, **Network Connectivity API**, **Service Consumer Management API**,
   **Compute Engine API**, **Identity-Aware Proxy API**.

## 1. VPC network

**VPC network** → **VPC networks** → **Create VPC network**:
- Name `hp-aicache-vpc`, subnet creation mode **Custom**.
- New subnet: name `hp-aicache-primary`, region **us-central1**, range `10.80.0.0/20`,
  **Private Google Access: On**.
- **Create**.

## 2. Firewall rule for browser SSH

**VPC network** → **Firewall** → **Create firewall rule**:
name `hp-aicache-allow-iap-ssh`, network `hp-aicache-vpc`, direction **Ingress**,
targets **Specified target tags** → `hp-aicache-vm`, source IPv4 range `35.235.240.0/20`
(Google's Identity-Aware Proxy), protocols **TCP 22** → **Create**.

> This lets the console's **SSH** button reach a VM that has no public IP. Nobody on the
> internet can connect.

## 3. Cloud NAT (outbound internet for pip)

**Network services** → **Cloud NAT** → **Create Cloud NAT gateway**: name `hp-aicache-nat`,
network `hp-aicache-vpc`, region us-central1, Cloud Router → **Create new router**
`hp-aicache-router` → **Create**.

## 4. Service account for the app

**IAM & Admin** → **Service accounts** → **Create service account**: name `hp-aicache-app`.
Grant roles: **Memorystore DB Connection User** (lets it sign in to the cache with IAM) and
**Memorystore Viewer** (lets it download the instance's CA certificate) → **Done**.

> **IAM authentication:** instead of a password, the app sends a Google access token that
> expires after an hour. The demo's `cache_client.py` refreshes it automatically.

## 5. Create the Memorystore for Valkey instance

**Memorystore** → **Valkey** → **Create instance**.

- **Instance ID** `hp-aicache-primary`.
- **Instance configuration:** **Cluster Mode Enabled**. Node type **shared-core-nano**
  (1.4 GB, cheapest, no SLA; production uses **highmem-medium**). Shards **1**
  (production 3). Replicas per shard **0** for the lab (production 1).
- **Location:** region **us-central1**, zone distribution **Multi-zone**.
- **Engine version:** Valkey **8.0** (or the newest offered).
- **Networking:** network `hp-aicache-vpc`. The console asks for a **service connection
  policy** the first time: **Create**, choose subnet `hp-aicache-primary`. Memorystore uses
  it to put private endpoints (Private Service Connect) into your subnet.
- **Security:** **IAM authentication: On**. **In-transit encryption: On** (keep the
  per-instance CA).
- **Persistence:** **Off**.
- **Configurations:** add `maxmemory-policy` = `volatile-lru`.
- **Labels:** `project = ai-infra-series`, `scenario = 09`.
- **Create.** Takes about 10 minutes.

When it is ready, open it and note the **discovery endpoint** IP and port (6379) on the
**Connections** tab.

> **Cluster mode:** the data is split across shards, and clients first ask the *discovery
> endpoint* which shard holds which keys. Use a cluster-aware client (the demo sets
> `CACHE_CLUSTER=1`). Vector search works across shards: each shard indexes its own keys
> and a search asks all of them.

## 6. Test VM (no external IP)

**Compute Engine** → **VM instances** → **Create instance**:
- Name `hp-aicache-vm`, region us-central1, zone `us-central1-a`, machine type **e2-medium**.
- Boot disk: **Debian 12**.
- **Networking:** network tags `hp-aicache-vm`; network interface → network `hp-aicache-vpc`,
  subnet `hp-aicache-primary`, **External IPv4 address: None**.
- **Security:** service account **hp-aicache-app**, access scopes **Allow full access to
  all Cloud APIs** (the IAM roles from step 4 still limit what it can do).
- **Advanced → Automation → Startup script:**

  ```bash
  apt-get update && apt-get install -y python3-venv git redis-tools
  [ -d /opt/ai-infra-labs ] || git clone https://github.com/pankajrudrawar/ai-infra-labs.git /opt/ai-infra-labs
  python3 -m venv /opt/venv
  /opt/venv/bin/pip install -r /opt/ai-infra-labs/scenarios/09-enterprise-ai-caching/app/requirements.txt
  chmod -R a+rwX /opt/ai-infra-labs /opt/venv
  ```
- **Create**.

## 7. Connect and get the CA certificate

VM list → **SSH** next to `hp-aicache-vm`. In the browser terminal:

```bash
sudo journalctl -u google-startup-scripts -f     # wait for pip to finish, then Ctrl+C

# Save every CA certificate of the instance (install all of them so CA rotation is painless)
gcloud memorystore instances get-certificate-authority hp-aicache-primary \
    --location=us-central1 --format=json \
  | python3 -c "import re,sys; t=sys.stdin.read().replace('\\\\n','\n'); print('\n'.join(re.findall(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', t, re.S)))" \
  > ~/server_ca.pem
grep -c BEGIN ~/server_ca.pem                     # 1 or more certificates

# Quick check with redis-cli: the password is a fresh access token
redis-cli -h <discovery-ip> -p 6379 --tls --cacert ~/server_ca.pem -c \
  -a "$(gcloud auth print-access-token)" --no-auth-warning PING
```

## 8. Run the demo (same code as Azure)

```bash
source /opt/venv/bin/activate && cd /opt/ai-infra-labs/scenarios/09-enterprise-ai-caching/app
export CACHE_HOST=<discovery-ip> CACHE_PORT=6379
export CACHE_TLS=1 CACHE_CA_FILE=$HOME/server_ca.pem CACHE_CLUSTER=1 CACHE_AUTH=gcp-iam

python3 cache_client.py
python3 demo.py --sweep
export CACHE_THRESHOLD=<value from the sweep>
python3 demo.py --no-cache -n 60
python3 demo.py -n 300
python3 demo.py --traps
python3 patterns_demo.py
```

Only the environment variables changed between clouds. That's the point to make in the
video: Valkey and Redis speak the same protocol, so the app doesn't care.

## 9. Watch it in the console

Instance → **Monitoring**: memory usage, CPU, connected clients, commands per second.
**Monitoring** → **Alerting** → **Create policy**: Memorystore instance memory usage ratio
above 0.75 for 5 minutes → email. Record the charts while `demo.py -n 300` runs.

## 10. Add a cross-region secondary and fail over

1. **VPC network** → `hp-aicache-vpc` → **Add subnet**: `hp-aicache-secondary`, region
   **us-east4**, `10.81.0.0/20`, Private Google Access on. (A VPC is global, so the VM in
   us-central1 can reach us-east4 with no extra networking.)
2. Open `hp-aicache-primary` → **Cross-region replication** → **Create secondary instance**:
   ID `hp-aicache-secondary`, region **us-east4**, same node type and shard count. Accept
   the prompt to create a service connection policy for the new subnet.
3. When it's ready, note its discovery IP and save its CA too (repeat the step 7 command
   with `hp-aicache-secondary` and `--location=us-east4`, appending `>>` to the same file).
4. Measure replication lag:

   ```bash
   READ_HOST=<secondary-discovery-ip> python3 replication_check.py
   ```

   The secondary is **read-only**: try `redis-cli ... SET x 1` against it and see the error.
5. **Failover drill:** on the secondary choose **Switchover** (planned, swaps roles) or
   **Detach** (unplanned: turns it into a standalone, writable primary). Point `CACHE_HOST`
   at it and run `demo.py -n 100`: cached answers are already there.

> **Azure vs. Google here:** Azure's geo-replication is active-active (write anywhere).
> Google's is active-passive (one writer, read-only secondaries you promote). See
> [comparison](comparison.md).

## 11. Tear down

Delete in this order: **Memorystore** instances (secondary first, then primary) →
**VM** → **Cloud NAT** and **Cloud Router** → **firewall rule** →
**Network Connectivity → Service connection policies** → **subnets** → **VPC**.
Or, if the project holds only this lab: **IAM & Admin** → **Settings** → **Shut down** the project.
Next day, check **Billing → Reports** filtered by label `scenario = 09`.

Next: [Automation](automation.md) rebuilds all of this with one command.
