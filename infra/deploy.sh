#!/usr/bin/env bash
# ============================================================
#  Deploys the Hotel Management System to Azure, end to end.
#
#  Usage:
#     ./deploy.sh                      # uses the defaults below
#     RG=my-rg LOCATION=westeurope ./deploy.sh
#
#  Prerequisites:
#     - Azure CLI installed and logged in  (az login)
#     - An SSH key pair at ~/.ssh/id_rsa.pub, or one is generated
#     - main.parameters.json filled in with your repo URL and email
# ============================================================
set -euo pipefail

RG="${RG:-rg-hotel-prod}"
LOCATION="${LOCATION:-centralindia}"
PARAM_FILE="${PARAM_FILE:-main.parameters.json}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_rsa.pub}"

say()  { printf '\n\033[1;32m==>\033[0m %s\n' "$1"; }
warn() { printf '\n\033[1;33m!!\033[0m %s\n' "$1"; }
die()  { printf '\n\033[1;31mxx\033[0m %s\n' "$1" >&2; exit 1; }

# ------------------------------------------------------------
#  0. Checks
# ------------------------------------------------------------
command -v az >/dev/null || die "Azure CLI not found. Install it first: https://aka.ms/azure-cli"
az account show >/dev/null 2>&1 || die "Not signed in. Run: az login"

[ -f "$PARAM_FILE" ] || die "Parameter file not found: $PARAM_FILE"

if grep -q "REPLACE_WITH" "$PARAM_FILE"; then
  die "$PARAM_FILE still contains REPLACE_WITH placeholders. Fill them in first."
fi

if [ ! -f "$SSH_KEY" ]; then
  warn "No SSH key at $SSH_KEY - generating one."
  ssh-keygen -t rsa -b 4096 -f "${SSH_KEY%.pub}" -N "" -q
fi

# ------------------------------------------------------------
#  1. Database password
#     Generated here and passed straight into the deployment,
#     which stores it in Key Vault. It is never written to disk.
# ------------------------------------------------------------
if [ -z "${DB_PASSWORD:-}" ]; then
  say "Generating a database password"
  # Azure MySQL requires 8-128 chars with three of: upper, lower, digit, symbol.
  DB_PASSWORD="$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-20)Aa1!"
fi

# ------------------------------------------------------------
#  2. Resource group
# ------------------------------------------------------------
say "Creating resource group '$RG' in $LOCATION"
az group create --name "$RG" --location "$LOCATION" --output none

# ------------------------------------------------------------
#  3. Validate before spending anything
# ------------------------------------------------------------
say "Validating the template"
az deployment group validate \
  --resource-group "$RG" \
  --template-file main.bicep \
  --parameters "@$PARAM_FILE" \
  --parameters adminSshPublicKey="$(cat "$SSH_KEY")" \
  --parameters dbAdminPassword="$DB_PASSWORD" \
  --output none \
  || die "Template validation failed. Nothing was deployed."

# ------------------------------------------------------------
#  4. Deploy
#     The Application Gateway alone takes several minutes, so the
#     whole run is usually 15-25 minutes on a first deployment.
# ------------------------------------------------------------
say "Deploying - this normally takes 15 to 25 minutes"
DEPLOY_NAME="hotel-$(date +%Y%m%d-%H%M%S)"
az deployment group create \
  --resource-group "$RG" \
  --name "$DEPLOY_NAME" \
  --template-file main.bicep \
  --parameters "@$PARAM_FILE" \
  --parameters adminSshPublicKey="$(cat "$SSH_KEY")" \
  --parameters dbAdminPassword="$DB_PASSWORD" \
  --output none

# ------------------------------------------------------------
#  5. Report what was built
# ------------------------------------------------------------
say "Reading deployment outputs"
OUTPUTS=$(az deployment group show \
  --resource-group "$RG" \
  --name "$DEPLOY_NAME" \
  --query properties.outputs -o json)

APP_URL=$(echo "$OUTPUTS"   | python3 -c 'import sys,json;print(json.load(sys.stdin)["applicationUrl"]["value"])')
MYSQL_HOST=$(echo "$OUTPUTS"| python3 -c 'import sys,json;print(json.load(sys.stdin)["mysqlHostname"]["value"])')
HA_ACTIVE=$(echo "$OUTPUTS" | python3 -c 'import sys,json;print(json.load(sys.stdin)["databaseHaActive"]["value"])')

if [ "$HA_ACTIVE" != "True" ] && [ "$HA_ACTIVE" != "true" ]; then
  warn "Database high availability is OFF. Burstable tiers do not support it; \
switch dbSkuName to Standard_D2ds_v4 in $PARAM_FILE to enable zone redundancy."
fi

# ------------------------------------------------------------
#  6. Load the schema
# ------------------------------------------------------------
say "Loading the database schema"
./load-schema.sh "$RG" || warn "Schema load did not complete - run ./load-schema.sh $RG by hand."

cat <<EOF

============================================================
  Deployment finished

  Application : $APP_URL
  MySQL host  : $MYSQL_HOST
  Resource gp : $RG

  Instances need a few minutes after deployment to finish
  installing packages before the gateway reports them healthy.

  Tear everything down with:  ./destroy.sh $RG
============================================================

EOF
