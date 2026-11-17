# Part E: Automate it (Terraform + GitHub Actions)

You built both sides by hand. Now the same design becomes code, so it is repeatable,
reviewable in a pull request, and identical every time.

## What's in the Terraform

| | `terraform/azure/` | `terraform/gcp/` |
| --- | --- | --- |
| Network | VNet per region, app + private-endpoint subnets, peering when geo is on | One global VPC, subnet per region, service connection policies (PSC) |
| Cache | `azurerm_managed_redis`: Balanced, RediSearch, Enterprise cluster, NoEviction, TLS only, keys disabled, public access off | `google_memorystore_instance`: cluster mode, multi-zone, IAM auth, TLS, `volatile-lru` |
| Second region | `azurerm_managed_redis_geo_replication` (active-active) | Secondary instance with `cross_instance_replication_config` (read-only) |
| Private access | Private endpoints + `privatelink.redis.azure.net` | PSC endpoints created automatically |
| App identity | User-assigned managed identity + `azurerm_managed_redis_access_policy_assignment` | Service account + `roles/memorystore.dbConnectionUser` |
| Test VM | Ubuntu B2s, no public IP, NAT gateway, Bastion Developer | Debian e2-medium, no external IP, Cloud NAT, IAP SSH |
| Lab defaults | Balanced_B3 with HA, one region | 1 × shared-core-nano, no replicas, one region |

Switch to the production design with variables only (see each `terraform.tfvars.example`).

## Run it from your laptop or Cloud Shell

Azure Cloud Shell and Google Cloud Shell both have Terraform installed and are already
signed in, so they are the easiest place to run this.

**Azure**

```bash
cd scenarios/09-enterprise-ai-caching/terraform/azure
cp terraform.tfvars.example terraform.tfvars      # fill in subscription, prefix, SSH key
terraform init
terraform plan -out tfplan                         # read it: what will be created?
terraform apply tfplan                             # billing starts here (asks nothing more)
terraform output demo_env                          # paste on the VM

# Second region:
terraform apply -var enable_geo_replication=true

terraform destroy                                  # end of session
```

**Google Cloud**

```bash
cd scenarios/09-enterprise-ai-caching/terraform/gcp
cp terraform.tfvars.example terraform.tfvars      # fill in project_id
terraform init && terraform plan -out tfplan && terraform apply tfplan
terraform output primary_endpoints                 # discovery IP for CACHE_HOST
terraform apply -var enable_cross_region=true      # second region
terraform destroy
```

Things that bite:

- **Changing these recreates the cache (data lost):** Azure `high_availability`,
  `clustering_policy`, modules, geo group name; Google `transit_encryption_mode`, mode,
  network. That's why the Azure primary starts as a one-member geo group.
- **Deletion protection** is off in the lab so `destroy` works. Turn it on in production
  (`deletion_protection = true` on Google; a `CanNotDelete` resource lock on Azure).
- **State** holds resource IDs and outputs. For a team, store it remotely (Azure Storage /
  GCS backend blocks are stubbed in `versions.tf`), never in git (`.gitignore` covers it).

## The CI pipeline

[`.github/workflows/scenario-09-iac.yml`](../../../.github/workflows/scenario-09-iac.yml)

| Trigger | Job | What it proves |
| --- | --- | --- |
| Every PR touching the scenario | `terraform-checks` (Azure + Google) | `fmt`, `init`, `validate`, `tflint` pass |
| | `security-scan` | Checkov report (soft-fail: lab defaults like "no deletion protection" are flagged on purpose) |
| | `python-checks` | `ruff` lint of the app, sizing script runs |
| Manual (**Actions → Scenario 09 IaC → Run workflow**) | `plan` | A real `terraform plan` against your cloud, uploaded as an artifact |

Nothing in the workflow applies or destroys anything. The enterprise pattern is:
**PR → automatic checks → plan → a human reads the plan → apply.** For the lab you apply
from your own shell after reading the plan.

### Optional: let GitHub plan with no stored keys (OIDC)

The `plan` job signs in with OpenID Connect: GitHub issues a short-lived token per run, and
each cloud trusts tokens from *this repository only*. No secret keys are stored in GitHub.

**Azure (portal):** **Microsoft Entra ID** → **App registrations** → **New registration**
`gh-ai-infra-labs-plan` → **Certificates & secrets** → **Federated credentials** →
**Add credential** → scenario **GitHub Actions deploying Azure resources**, organization
`pankajrudrawar`, repository `ai-infra-labs`, entity **Branch** `main` (add a second one for
**Pull request** if you want). Then **Subscriptions** → your lab subscription →
**Access control (IAM)** → **Add role assignment** → **Reader** to the app.
Add repo secrets `AZURE_CLIENT_ID` (the app's client ID), `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

**Google Cloud (console):** **IAM & Admin** → **Workload Identity Federation** →
**Create pool** `github` → provider **OpenID Connect**, issuer
`https://token.actions.githubusercontent.com`, attribute mapping
`google.subject = assertion.sub`, `attribute.repository = assertion.repository`, condition
`assertion.repository == "pankajrudrawar/ai-infra-labs"`. Create a service account
`gh-plan` with **Viewer**, and grant the pool **Workload Identity User** on it.
Add repo secrets `GCP_WORKLOAD_IDENTITY_PROVIDER` (the provider's full resource name),
`GCP_SERVICE_ACCOUNT`, `GCP_PROJECT_ID`.

Read-only roles are enough for `plan`. Give a pipeline write access only once you add an
`apply` job behind a GitHub **environment** with required reviewers.
