// ============================================================
//  Virtual Machine Scale Set running the Streamlit application,
//  with autoscale rules and a managed identity that can read the
//  database password out of Key Vault.
// ============================================================

@description('Azure region.')
param location string

@description('Prefix applied to every resource name.')
param prefix string

@description('Resource id of the application subnet.')
param appSubnetId string

@description('Resource id of the Application Gateway backend pool to join.')
param backendPoolId string

@description('Administrator username for the virtual machines.')
param adminUsername string

@description('SSH public key for the administrator account.')
param adminSshPublicKey string

@description('Cloud-init document, already base64 encoded.')
param customDataBase64 string

@description('Instance count the scale set starts with and never drops below.')
@minValue(1)
@maxValue(10)
param minInstances int = 2

@description('Largest number of instances autoscale may create.')
@minValue(2)
@maxValue(20)
param maxInstances int = 6

@description('Virtual machine size.')
param vmSize string = 'Standard_B2s'

@description('Name of the Key Vault whose secrets the instances may read.')
param keyVaultName string

var scaleSetName = '${prefix}-vmss'

// Built-in role that allows reading secret values, nothing else.
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource scaleSet 'Microsoft.Compute/virtualMachineScaleSets@2023-09-01' = {
  name: scaleSetName
  location: location
  // Spreading instances across both zones means losing one datacentre
  // removes capacity but not availability.
  zones: [ '1', '2' ]
  sku: {
    name: vmSize
    tier: 'Standard'
    capacity: minInstances
  }
  identity: {
    // A system-assigned identity means no credential of any kind is
    // stored on the machine or in the source code.
    type: 'SystemAssigned'
  }
  properties: {
    orchestrationMode: 'Uniform'
    overprovision: false
    zoneBalance: true
    upgradePolicy: {
      mode: 'Automatic'
    }
    virtualMachineProfile: {
      osProfile: {
        computerNamePrefix: take('${prefix}vm', 9)
        adminUsername: adminUsername
        customData: customDataBase64
        linuxConfiguration: {
          // Password authentication disabled; SSH keys only.
          disablePasswordAuthentication: true
          ssh: {
            publicKeys: [
              {
                path: '/home/${adminUsername}/.ssh/authorized_keys'
                keyData: adminSshPublicKey
              }
            ]
          }
          provisionVMAgent: true
        }
      }
      storageProfile: {
        imageReference: {
          publisher: 'Canonical'
          offer: '0001-com-ubuntu-server-jammy'
          sku: '22_04-lts-gen2'
          version: 'latest'
        }
        osDisk: {
          createOption: 'FromImage'
          caching: 'ReadWrite'
          managedDisk: {
            storageAccountType: 'StandardSSD_LRS'
          }
        }
      }
      networkProfile: {
        networkInterfaceConfigurations: [
          {
            name: '${prefix}-nic'
            properties: {
              primary: true
              ipConfigurations: [
                {
                  name: '${prefix}-ipconfig'
                  properties: {
                    subnet: { id: appSubnetId }
                    // Joining the gateway's backend pool here is what
                    // makes new instances receive traffic automatically.
                    applicationGatewayBackendAddressPools: [
                      { id: backendPoolId }
                    ]
                  }
                }
              ]
            }
          }
        ]
      }
    }
  }
}

// ------------------------------------------------------------
//  Let the scale set's identity read secrets from the vault.
// ------------------------------------------------------------
resource vault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource secretsUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: vault
  // The name must be a GUID that is stable for this pairing, so that
  // redeploying does not try to create a second identical assignment.
  name: guid(vault.id, scaleSet.id, keyVaultSecretsUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: scaleSet.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ------------------------------------------------------------
//  Autoscale: the elasticity the report claims.
// ------------------------------------------------------------
resource autoscale 'Microsoft.Insights/autoscalesettings@2022-10-01' = {
  name: '${prefix}-autoscale'
  location: location
  properties: {
    enabled: true
    targetResourceUri: scaleSet.id
    profiles: [
      {
        name: 'cpuBasedProfile'
        capacity: {
          minimum: string(minInstances)
          maximum: string(maxInstances)
          default: string(minInstances)
        }
        rules: [
          {
            // Scale out when the fleet is busy.
            metricTrigger: {
              metricName: 'Percentage CPU'
              metricResourceUri: scaleSet.id
              timeGrain: 'PT1M'
              statistic: 'Average'
              timeWindow: 'PT5M'
              timeAggregation: 'Average'
              operator: 'GreaterThan'
              threshold: 70
            }
            scaleAction: {
              direction: 'Increase'
              type: 'ChangeCount'
              value: '1'
              // Wait before acting again, so one burst does not
              // trigger several scale-outs in a row.
              cooldown: 'PT5M'
            }
          }
          {
            // Scale back in when it is quiet. The window is longer
            // than the scale-out window to avoid flapping.
            metricTrigger: {
              metricName: 'Percentage CPU'
              metricResourceUri: scaleSet.id
              timeGrain: 'PT1M'
              statistic: 'Average'
              timeWindow: 'PT10M'
              timeAggregation: 'Average'
              operator: 'LessThan'
              threshold: 30
            }
            scaleAction: {
              direction: 'Decrease'
              type: 'ChangeCount'
              value: '1'
              cooldown: 'PT10M'
            }
          }
        ]
      }
    ]
  }
}

output scaleSetId string = scaleSet.id
output scaleSetName string = scaleSet.name
output principalId string = scaleSet.identity.principalId
