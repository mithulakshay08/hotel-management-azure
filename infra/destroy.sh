#!/usr/bin/env bash
# ============================================================
#  Deletes every resource created by deploy.sh.
#
#  Run this as soon as a demonstration finishes. An idle
#  Application Gateway and MySQL server continue to bill by the
#  hour, and a student subscription is quickly exhausted by a
#  deployment left running over a weekend.
#
#  Usage:  ./destroy.sh [resource-group]
# ============================================================
set -euo pipefail

RG="${1:-rg-hotel-prod}"

command -v az >/dev/null || { echo "Azure CLI not found." >&2; exit 1; }

if ! az group show --name "$RG" >/dev/null 2>&1; then
  echo "Resource group '$RG' does not exist. Nothing to do."
  exit 0
fi

echo
echo "This permanently deletes the resource group '$RG' and everything in it:"
az resource list --resource-group "$RG" --query '[].{name:name, type:type}' -o table
echo

read -r -p "Type the resource group name to confirm: " CONFIRM
[ "$CONFIRM" = "$RG" ] || { echo "Names did not match. Nothing deleted."; exit 1; }

echo "Deleting '$RG' - this runs in the background and takes a few minutes."
az group delete --name "$RG" --yes --no-wait

# Key Vault has soft-delete on, so the name stays reserved for the
# retention period. Purge it if the name needs to be reusable now.
cat <<'EOF'

Deletion started.

Note: the Key Vault is soft-deleted, so its name stays reserved for
seven days. If you need to redeploy with the same name immediately:

    az keyvault purge --name <vault-name>

EOF
