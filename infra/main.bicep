// ============================================================
//  Hotel Management System - Azure deployment
//  22AIE303 / Cloud Computing project, Team 03
//
//  Deploy with:
//    az group create -n rg-hotel-prod -l centralindia
//    az deployment group create -g rg-hotel-prod \
//       -f main.bicep -p @main.parameters.json
// ============================================================

targetScope = 'resourceGroup'

// ---------------------------- parameters ----------------------------

@description('Azure region. Must support Availability Zones for the HA options to work.')
param location string = resourceGroup().location

@description('Short prefix for every resource name. Lower-case letters and digits only.')
@minLength(3)
@maxLength(11)
param prefix string = 'hotel'

@description('Administrator username for the virtual machines.')
param adminUsername string = 'azureuser'

@description('SSH public key for the VM administrator account.')
param adminSshPublicKey string

@description('MySQL administrator login.')
param dbAdminLogin string = 'hoteladmin'

@secure()
@description('MySQL administrator password. Pass at deploy time; never commit it.')
param dbAdminPassword string

@description('Public git repository holding the application source.')
param repositoryUrl string

@description('Email address for monitoring alerts.')
param alertEmail string

@description('MySQL compute tier. Burstable is cheapest; GeneralPurpose is required for HA.')
@allowed([
  'Standard_B1ms'
  'Standard_B2s'
  'Standard_D2ds_v4'
  'Standard_D4ds_v4'
])
param dbSkuName string = 'Standard_B1ms'

@description('Turn on zone-redundant database HA. Ignored on Burstable tiers, which cannot support it.')
param enableDatabaseHa bool = false

@description('Smallest number of application instances.')
@minValue(1)
@maxValue(10)
param minInstances int = 2

@description('Largest number of application instances autoscale may create.')
@minValue(2)
@maxValue(20)
param maxInstances int = 6

@description('Virtual machine size for the application tier.')
param vmSize string = 'Standard_B2s'

// ---------------------------- networking ----------------------------

module network 'modules/network.bicep' = {
  name: 'deploy-network'
  params: {
    location: location
    prefix: prefix
  }
}

// ---------------------------- secrets -------------------------------

module keyvault 'modules/keyvault.bicep' = {
  name: 'deploy-keyvault'
  params: {
    location: location
    prefix: prefix
    appSubnetId: network.outputs.appSubnetId
    databasePassword: dbAdminPassword
  }
}

// ---------------------------- database ------------------------------

module database 'modules/database.bicep' = {
  name: 'deploy-database'
  params: {
    location: location
    prefix: prefix
    dataSubnetId: network.outputs.dataSubnetId
    vnetId: network.outputs.vnetId
    administratorLogin: dbAdminLogin
    administratorPassword: dbAdminPassword
    skuName: dbSkuName
    enableHighAvailability: enableDatabaseHa
  }
}

// ---------------------------- entry point ---------------------------

module gateway 'modules/gateway.bicep' = {
  name: 'deploy-gateway'
  params: {
    location: location
    prefix: prefix
    gatewaySubnetId: network.outputs.gatewaySubnetId
  }
}

// ---------------------------- application ---------------------------

// The cloud-init document is read at compile time and its placeholders
// replaced with values only known once the other modules exist.
var cloudInitRaw = loadTextContent('cloud-init.yaml')
var cloudInitRendered = replace(
  replace(
    replace(
      replace(
        replace(cloudInitRaw, '__KEYVAULT_NAME__', keyvault.outputs.vaultName),
        '__SECRET_NAME__', keyvault.outputs.secretName),
      '__MYSQL_FQDN__', database.outputs.fullyQualifiedDomainName),
    '__DB_USER__', dbAdminLogin),
  '__DB_NAME__', database.outputs.databaseName)

var cloudInitFinal = replace(cloudInitRendered, '__REPO_URL__', repositoryUrl)

module compute 'modules/compute.bicep' = {
  name: 'deploy-compute'
  params: {
    location: location
    prefix: prefix
    appSubnetId: network.outputs.appSubnetId
    backendPoolId: gateway.outputs.backendPoolId
    adminUsername: adminUsername
    adminSshPublicKey: adminSshPublicKey
    customDataBase64: base64(cloudInitFinal)
    minInstances: minInstances
    maxInstances: maxInstances
    vmSize: vmSize
    keyVaultName: keyvault.outputs.vaultName
  }
}

// ---------------------------- monitoring ----------------------------

module monitoring 'modules/monitoring.bicep' = {
  name: 'deploy-monitoring'
  params: {
    location: location
    prefix: prefix
    scaleSetId: compute.outputs.scaleSetId
    alertEmail: alertEmail
  }
}

// ---------------------------- outputs -------------------------------

@description('Open this address in a browser once the instances finish booting.')
output applicationUrl string = 'http://${gateway.outputs.publicFqdn}'

@description('Hostname to put in db_config.py if connecting from elsewhere.')
output mysqlHostname string = database.outputs.fullyQualifiedDomainName

output keyVaultName string = keyvault.outputs.vaultName
output scaleSetName string = compute.outputs.scaleSetName
output logAnalyticsWorkspace string = monitoring.outputs.workspaceName

@description('False when a Burstable tier silently disabled the HA request.')
output databaseHaActive bool = database.outputs.highAvailabilityEnabled
