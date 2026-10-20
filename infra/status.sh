#!/usr/bin/env bash
# ============================================================
#  Shows whether the deployment is healthy, and what it is costing.
#
#  Run this a few minutes after deploy.sh finishes. The instances
#  need time to install packages before the gateway will call them
#  healthy, so "Unhealthy" immediately after a deploy is normal.
#
#  Usage:  ./status.sh [resource-group]
# ============================================================
set -euo pipefail

RG="${1:-rg-hotel-prod}"

say() { printf '\n\033[1;32m==>\033[0m %s\n' "$1"; }
die() { printf '\n\033[1;31mxx\033[0m %s\n' "$1" >&2; exit 1; }

command -v az >/dev/null || die "Azure CLI not found."
az group show --name "$RG" >/dev/null 2>&1 || die "Resource group '$RG' does not exist."

# ------------------------------------------------------------
say "Resources in $RG"
az resource list --resource-group "$RG" \
  --query '[].{Name:name, Type:type}' -o table

# ------------------------------------------------------------
say "Application instances"
VMSS=$(az vmss list -g "$RG" --query '[0].name' -o tsv 2>/dev/null || true)
if [ -n "$VMSS" ]; then
  az vmss list-instances -g "$RG" -n "$VMSS" \
    --query '[].{ID:instanceId, State:provisioningState, Zone:zones[0]}' -o table
  COUNT=$(az vmss list-instances -g "$RG" -n "$VMSS" --query 'length(@)' -o tsv)
  echo "Running instances: $COUNT"
else
  echo "No scale set found yet."
fi

# ------------------------------------------------------------
say "Gateway backend health"
AGW=$(az network application-gateway list -g "$RG" --query '[0].name' -o tsv 2>/dev/null || true)
if [ -n "$AGW" ]; then
  # This call can take a few seconds; it probes the backends live.
  az network application-gateway show-backend-health \
    -g "$RG" -n "$AGW" \
    --query 'backendAddressPools[0].backendHttpSettingsCollection[0].servers[].{Address:address, Health:health}' \
    -o table 2>/dev/null || echo "Backend health not available yet."

  IP=$(az network public-ip list -g "$RG" --query '[0].ipAddress' -o tsv)
  FQDN=$(az network public-ip list -g "$RG" --query '[0].dnsSettings.fqdn' -o tsv)
  echo
  echo "Application URL : http://${FQDN:-$IP}"
else
  echo "No application gateway found yet."
fi

# ------------------------------------------------------------
say "Database"
MYSQL=$(az mysql flexible-server list -g "$RG" --query '[0].name' -o tsv 2>/dev/null || true)
if [ -n "$MYSQL" ]; then
  az mysql flexible-server show -g "$RG" -n "$MYSQL" \
    --query '{Name:name, State:state, Tier:sku.tier, HA:highAvailability.mode, Version:version}' \
    -o table
else
  echo "No MySQL server found yet."
fi

# ------------------------------------------------------------
cat <<'EOF'

------------------------------------------------------------
  Reminder: this environment bills by the hour while it exists.
  The Application Gateway is the largest single charge.

  When the demonstration is over:   ./destroy.sh
------------------------------------------------------------

EOF
