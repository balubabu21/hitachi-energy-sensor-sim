#!/usr/bin/env bash
# Provision Azure infrastructure, build images in ACR and deploy both container apps.
# Requires: Azure CLI (logged in: `az login`), Terraform >= 1.6.
# Images are built by ACR Tasks in the cloud (linux/amd64), so Docker is NOT needed locally.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF_DIR="$ROOT/infra/terraform"
TAG="${IMAGE_TAG:-$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)}"

cd "$TF_DIR"
[ -f terraform.tfvars ] || { echo "Create $TF_DIR/terraform.tfvars (see terraform.tfvars.example)"; exit 1; }

echo "==> Registering Azure Container Apps resource provider"
az provider register --namespace Microsoft.App --wait

terraform init -upgrade

echo "==> 1/3 Creating resource group, registry and identity"
terraform apply -auto-approve \
  -target=azurerm_container_registry.this \
  -target=azurerm_role_assignment.acr_pull

ACR="$(terraform output -raw acr_name)"

echo "==> 2/3 Building images in ACR ($ACR) with tag $TAG"
az acr build --registry "$ACR" --image "backend:$TAG"  --platform linux/amd64 "$ROOT/backend"
az acr build --registry "$ACR" --image "frontend:$TAG" --platform linux/amd64 "$ROOT/frontend"

echo "==> 3/3 Deploying Container Apps"
terraform apply -auto-approve -var "image_tag=$TAG"

echo
echo "Deployed: $(terraform output -raw frontend_url)"
