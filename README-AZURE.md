# Azure Deployment Guide

This guide documents the Azure deployment of the Grid Sensor Simulator: what was provisioned,
why each Azure service is used, how to deploy updates, and how to remove the deployment.
The application is an unofficial simulator; generated sensor readings are engineering assumptions,
not Hitachi Energy specifications.

## Live deployment

- **Web application:** https://ca-hesensor-dev-web.gentlesea-c635cf92.uksouth.azurecontainerapps.io
- **API health check:** https://ca-hesensor-dev-web.gentlesea-c635cf92.uksouth.azurecontainerapps.io/api/health

The backend API is private to the Container Apps environment. Use the frontend's `/api/*` proxy
for API requests from outside Azure. FastAPI's `/docs` page is not exposed publicly; it is available
when running the backend locally at http://localhost:8000/docs.

## Why deploy to Azure?

Azure hosts the web app at a public HTTPS endpoint without requiring a developer's computer or
local Docker daemon to stay running. The app images are built in Azure Container Registry Tasks,
and Azure Container Apps runs the frontend and API as separate services. The Consumption plan
scales the apps down to zero replicas when idle, helping limit compute charges for a small,
intermittently used project.

Terraform describes the infrastructure as code. This makes the resource setup repeatable, records
the desired configuration in reviewable files, and lets Terraform show planned changes before they
are applied. Container Apps' managed identity pulls images from the private registry without
storing registry passwords in Terraform or the application configuration.

## Architecture

```text
Browser
  │ HTTPS
  ▼
Public Container App: Next.js frontend (port 3000)
  │ runtime /api/* proxy using BACKEND_URL
  ▼
Internal-only Container App: FastAPI backend (port 8000)
  │
  ├── images pulled from private Azure Container Registry using managed identity
  └── platform logs sent to Log Analytics
```

The frontend is the only app with external ingress. The backend has internal ingress and is not
directly internet-accessible. Its health probes use `/api/health`. Both apps use HTTP scaling rules,
zero minimum replicas, and a maximum of three replicas.

## Azure resources

Terraform creates these resources in **UK South**:

| Resource | Purpose |
|---|---|
| Resource group `rg-hesensor-dev` | Holds the application's Azure resources and tags them as a Terraform-managed workload. |
| Azure Container Registry (Basic) `acrhesensordevicfra` | Private image registry, with admin/password authentication disabled. |
| User-assigned managed identity `id-hesensor-dev-apps` | Shared identity used by the apps to authenticate to ACR. |
| `AcrPull` role assignment | Grants that identity permission to pull images from this registry only. |
| Log Analytics workspace `log-hesensor-dev-icfra` | Receives Container Apps environment logs; configured with 30-day retention. |
| Container Apps environment `cae-hesensor-dev` | Consumption environment hosting the two apps and their internal network connection. |
| Backend Container App `ca-hesensor-dev-api` | FastAPI API, 0.25 vCPU / 0.5 GiB per replica, internal ingress on port 8000. |
| Frontend Container App `ca-hesensor-dev-web` | Next.js app, 0.5 vCPU / 1 GiB per replica, public ingress on port 3000. |

Terraform also generates a short random suffix for globally unique names such as the registry and
Log Analytics workspace.

### Container images

- **Backend:** Python 3.12 slim image, FastAPI served by Uvicorn, running as a non-root user.
- **Frontend:** multi-stage Node.js 22 Alpine image; Next.js standalone production output runs as a
  non-root user.
- Both image repositories are private. The Container Apps pull their images through the managed
  identity, not a registry admin password.
- Builds run in ACR Tasks, so Docker is not required on the machine running the deploy script.

## Terraform and deployment files

- `infra/terraform/main.tf` declares the resource group, registry, managed identity, role
  assignment, Log Analytics workspace, Container Apps environment, and both apps.
- `infra/terraform/variables.tf` defines subscription, region, image tag, and replica settings.
- `infra/terraform/versions.tf` requires Terraform 1.6 or newer and pins the AzureRM 4.x and
  Random 3.x provider families. `.terraform.lock.hcl` records the selected provider builds and
  should be committed to source control.
- `infra/terraform/outputs.tf` exposes the app URLs, registry, and resource group.
- `infra/terraform/terraform.tfvars.example` is a safe template. The actual
  `terraform.tfvars` is local and git-ignored; it contains the subscription ID.
- `scripts/deploy.sh` registers the Container Apps resource provider, initializes Terraform,
  provisions the registry and image-pull identity, builds and pushes both images, then applies
  the full stack.
- `scripts/destroy.sh` runs `terraform destroy` for the configured Terraform state.

Terraform state and `terraform.tfvars` must not be committed. Terraform state can contain
infrastructure details and sensitive values. The current deployment uses local state, which is
appropriate only for an individual local workflow. For shared or automated deployments, configure
an access-controlled remote state backend with locking and backups before sharing Terraform
operations.

## Prerequisites and first-time setup

You need:

- An Azure subscription and permission to create the listed resources and assign the `AcrPull` role.
- Azure CLI and Terraform 1.6 or newer.
- Access to complete interactive Azure sign-in and any required MFA.

From the project root, sign in and select the target subscription:

```bash
az login
az account set --subscription <subscription-id>
az account show --query "{name:name,id:id,state:state}" -o table
```

Create the ignored Terraform variables file from the example and set the subscription ID:

```bash
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
```

Edit `infra/terraform/terraform.tfvars` so `subscription_id` is the same subscription selected
above. Review the region, project name, and replica limits before deployment.

Initialize Terraform and inspect the proposed infrastructure changes:

```bash
cd infra/terraform
terraform init
terraform plan
cd ../..
```

Review the plan before proceeding. The deployment script applies Terraform automatically, so only
run it once you intend to create billable Azure resources:

```bash
./scripts/deploy.sh
```

The script prints the public frontend URL after a successful deployment. Its image tag defaults to
the current Git commit when available, or a timestamp otherwise.

## Update an existing deployment

After changing application code or container configuration, run the deploy script again:

```bash
./scripts/deploy.sh
```

It builds new backend and frontend images, pushes them to ACR, and updates the Container Apps to
use the new image tag. You can explicitly set a tag if needed:

```bash
IMAGE_TAG=my-release-1 ./scripts/deploy.sh
```

Keep the Terraform state and variables file used by the original deployment. Terraform needs that
state to update the existing resources rather than treat them as a separate deployment.

## Cost considerations

This is a Pay-As-You-Go deployment. Charges depend on region, account offer, currency, taxes,
usage, and Azure price changes.

- The Basic registry in UK South was listed at approximately **US$0.1666 per day** (about
  **US$5 per 30 days**) when this deployment was set up. It continues to incur a charge while it
  exists, even if the apps are idle. Basic includes up to 10 GB of registry storage.
- Container Apps use the Consumption plan and scale to zero. Compute, requests, and logging may
  have subscription-level free grants, but usage beyond applicable grants can be charged.
- ACR image-build time, Log Analytics ingestion/retention, and network transfer can add variable
  charges.
- Stopping or scaling the apps to zero does not delete the registry, workspace, or other resources.
  Destroy resources you no longer need to avoid ongoing charges.

Check current prices for your subscription in the [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/)
and monitor actual usage in Azure Cost Management. A budget alert notifies you; it does not stop
resources or prevent charges.

## Verify the deployment

Replace the URL below if Terraform outputs a different frontend address:

```bash
APP_URL=https://ca-hesensor-dev-web.gentlesea-c635cf92.uksouth.azurecontainerapps.io
curl -fsS "$APP_URL/api/health"
curl -fsS "$APP_URL/api/products"
```

The health endpoint should return `{"status":"ok"}`. The products endpoint should return the
catalogue; this deployment currently contains 23 product families.

To inspect app status and logs:

```bash
az containerapp list --resource-group rg-hesensor-dev -o table
az containerapp logs show --name ca-hesensor-dev-api \
  --resource-group rg-hesensor-dev --type console --tail 50
az containerapp logs show --name ca-hesensor-dev-web \
  --resource-group rg-hesensor-dev --type console --tail 50
```

## Remove the deployment

From the project root, with the same subscription selected and the original Terraform state
available:

```bash
./scripts/destroy.sh
```

This deletes the Terraform-managed Azure resources in the deployment. Confirm the Terraform plan
before approving destruction. Back up any data you want to keep first. The local Terraform state
and variables file remain on your machine and are ignored by Git.
