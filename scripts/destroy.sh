#!/usr/bin/env bash
# Tear down every Azure resource created by deploy.sh.
set -euo pipefail
cd "$(dirname "$0")/../infra/terraform"
terraform destroy
