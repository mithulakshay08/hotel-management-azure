#!/usr/bin/env bash
# ============================================================
#  Loads 01_schema.sql into the Azure MySQL server.
#
#  The database uses private (VNet-integrated) access, so there is
#  deliberately no route to it from the internet - not from a laptop
#  and not from Cloud Shell. The schema is therefore loaded by asking
#  an application instance, which is already inside the VNet, to run
#  the import on our behalf.
#
#  'az vmss run-command invoke' does this through the Azure agent,
#  so it needs no SSH, no public IP and no bastion host.
#
#  Usage:  ./load-schema.sh [resource-group]
# ============================================================
set -euo pipefail

RG="${1:-rg-hotel-prod}"

say()  { printf '\n\033[1;32m==>\033[0m %s\n' "$1"; }
die()  { printf '\n\033[1;31mxx\033[0m %s\n' "$1" >&2; exit 1; }

command -v az >/dev/null || die "Azure CLI not found."

VMSS_NAME=$(az vmss list -g "$RG" --query '[0].name' -o tsv)
[ -n "$VMSS_NAME" ] || die "No scale set found in resource group $RG."

INSTANCE_ID=$(az vmss list-instances -g "$RG" -n "$VMSS_NAME" \
  --query '[0].instanceId' -o tsv)
[ -n "$INSTANCE_ID" ] || die "Scale set $VMSS_NAME has no running instances yet."

say "Running the import on $VMSS_NAME instance $INSTANCE_ID"

# The instance already holds the repository (cloned by cloud-init) and can
# read the database password from Key Vault with its managed identity, so
# no credential travels over this command.
read -r -d '' SCRIPT <<'REMOTE' || true
set -euo pipefail

CONFIG=/opt/hotel/app/db_config.py
SCHEMA=$(find /opt/hotel/src -name '01_schema.sql' -print -quit)

if [ -z "$SCHEMA" ]; then
  echo "01_schema.sql not found in the cloned repository" >&2
  exit 1
fi

# Reuse the values cloud-init already wrote, rather than re-deriving them.
HOST=$(python3 -c "import sys;sys.path.insert(0,'/opt/hotel/app');from db_config import DB_CONFIG;print(DB_CONFIG['host'])")
USER=$(python3 -c "import sys;sys.path.insert(0,'/opt/hotel/app');from db_config import DB_CONFIG;print(DB_CONFIG['user'])")
PASS=$(python3 -c "import sys;sys.path.insert(0,'/opt/hotel/app');from db_config import DB_CONFIG;print(DB_CONFIG['password'])")

# Azure MySQL requires TLS by default.
mysql --host="$HOST" --user="$USER" --password="$PASS" \
      --ssl-mode=REQUIRED < "$SCHEMA"

mysql --host="$HOST" --user="$USER" --password="$PASS" \
      --ssl-mode=REQUIRED -e "
        SELECT COUNT(*) AS tables_created
        FROM information_schema.tables
        WHERE table_schema='hotel_db' AND table_type='BASE TABLE';
        SELECT COUNT(*) AS rooms_loaded FROM hotel_db.rooms;"
REMOTE

RESULT=$(az vmss run-command invoke \
  --resource-group "$RG" \
  --name "$VMSS_NAME" \
  --instance-id "$INSTANCE_ID" \
  --command-id RunShellScript \
  --scripts "$SCRIPT" \
  --query 'value[0].message' -o tsv)

echo "$RESULT"

if echo "$RESULT" | grep -qi "tables_created"; then
  say "Schema loaded."
else
  die "Import did not report success - read the output above."
fi
