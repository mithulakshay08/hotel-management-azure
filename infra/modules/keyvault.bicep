// ============================================================
//  Azure Key Vault - holds the database password so that no
//  credential is ever written into the application source.
// ============================================================

@description('Azure region.')
param location string

@description('Prefix applied to every resource name.')
param prefix string

@description('Resource id of the application subnet, allowed to reach the vault.')
param appSubnetId string

@secure()
@description('Database administrator password to store as a secret.')
param databasePassword string

// Vault names are globally unique and limited to 24 characters,
// so a short hash of the resource group id keeps them collision-free.
var vaultName = take('${prefix}kv${uniqueString(resourceGroup().id)}', 24)

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    // Azure RBAC rather than legacy access policies: permissions are
    // granted as role assignments, which is the current recommended model.
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
      virtualNetworkRules: [
        { id: appSubnetId }
      ]
    }
  }
}

resource dbPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: vault
  name: 'mysql-admin-password'
  properties: {
    value: databasePassword
  }
}

output vaultName string = vault.name
output vaultUri string = vault.properties.vaultUri
output vaultId string = vault.id
output secretName string = dbPasswordSecret.name
