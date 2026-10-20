// ============================================================
//  Azure Database for MySQL - Flexible Server
//  Private (VNet-integrated) access, optional zone-redundant HA
// ============================================================

@description('Azure region.')
param location string

@description('Prefix applied to every resource name.')
param prefix string

@description('Resource id of the delegated data subnet.')
param dataSubnetId string

@description('Resource id of the virtual network, for the private DNS link.')
param vnetId string

@description('Administrator login for the MySQL server.')
param administratorLogin string

@secure()
@description('Administrator password. Never hard-code this; pass it at deploy time.')
param administratorPassword string

@description('Compute tier. Burstable is the cheapest and suits a student deployment.')
@allowed([
  'Standard_B1ms'
  'Standard_B2s'
  'Standard_D2ds_v4'
  'Standard_D4ds_v4'
])
param skuName string = 'Standard_B1ms'

@description('Enable zone-redundant high availability. Requires a GeneralPurpose SKU - Burstable tiers do not support it.')
param enableHighAvailability bool = false

@description('Days to retain automated backups (7-35).')
@minValue(7)
@maxValue(35)
param backupRetentionDays int = 7

var serverName = '${prefix}-mysql'
var privateDnsZoneName = '${prefix}-mysql.private.mysql.database.azure.com'

// Burstable tiers cannot run zone-redundant HA. Rather than letting the
// deployment fail at the API, resolve the tier from the SKU and only turn
// HA on when both the flag and the tier allow it.
var isBurstable = startsWith(skuName, 'Standard_B')
var skuTier = isBurstable ? 'Burstable' : 'GeneralPurpose'
var haEnabled = enableHighAvailability && !isBurstable

// ------------------------------------------------------------
//  Private DNS zone, so the application resolves the server to
//  a private address inside the VNet.
// ------------------------------------------------------------
resource privateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: privateDnsZoneName
  location: 'global'
}

resource dnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZone
  name: '${prefix}-mysql-vnet-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: vnetId }
  }
}

// ------------------------------------------------------------
//  The server itself
// ------------------------------------------------------------
resource mysql 'Microsoft.DBforMySQL/flexibleServers@2023-12-30' = {
  name: serverName
  location: location
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    version: '8.0.21'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    storage: {
      storageSizeGB: 20
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: haEnabled ? 'ZoneRedundant' : 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: dataSubnetId
      privateDnsZoneResourceId: privateDnsZone.id
    }
  }
  dependsOn: [ dnsLink ]
}

// ------------------------------------------------------------
//  Server parameter: allow the project's triggers and stored
//  procedure to be created without SUPER privilege.
//  Azure MySQL enables binary logging by default, which otherwise
//  blocks CREATE TRIGGER / CREATE PROCEDURE for a non-admin user.
// ------------------------------------------------------------
resource trustFunctionCreators 'Microsoft.DBforMySQL/flexibleServers/configurations@2023-12-30' = {
  parent: mysql
  name: 'log_bin_trust_function_creators'
  properties: {
    value: 'ON'
    source: 'user-override'
  }
}

// The application database. Character set matches the local schema.
resource hotelDb 'Microsoft.DBforMySQL/flexibleServers/databases@2023-12-30' = {
  parent: mysql
  name: 'hotel_db'
  properties: {
    charset: 'utf8mb4'
    collation: 'utf8mb4_unicode_ci'
  }
}

output serverName string = mysql.name
output fullyQualifiedDomainName string = mysql.properties.fullyQualifiedDomainName
output databaseName string = hotelDb.name
output highAvailabilityEnabled bool = haEnabled
