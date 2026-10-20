// ============================================================
//  Application Gateway v2 - public entry point, layer-7 load
//  balancing and health probing in front of the scale set.
// ============================================================

@description('Azure region.')
param location string

@description('Prefix applied to every resource name.')
param prefix string

@description('Resource id of the gateway subnet.')
param gatewaySubnetId string

@description('Port the application listens on inside the VMs.')
param appPort int = 8501

var gatewayName = '${prefix}-appgw'
var publicIpName = '${prefix}-pip'

// Standard SKU public IP, spread across both zones so the entry
// point survives the loss of one datacentre.
resource publicIp 'Microsoft.Network/publicIPAddresses@2023-11-01' = {
  name: publicIpName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  zones: [ '1', '2' ]
  properties: {
    publicIPAllocationMethod: 'Static'
    dnsSettings: {
      domainNameLabel: '${prefix}-${uniqueString(resourceGroup().id)}'
    }
  }
}

resource appGateway 'Microsoft.Network/applicationGateways@2023-11-01' = {
  name: gatewayName
  location: location
  zones: [ '1', '2' ]
  properties: {
    sku: {
      name: 'Standard_v2'
      tier: 'Standard_v2'
    }
    // The gateway scales itself between two and ten instances.
    autoscaleConfiguration: {
      minCapacity: 2
      maxCapacity: 10
    }
    gatewayIPConfigurations: [
      {
        name: 'gatewayIpConfig'
        properties: {
          subnet: { id: gatewaySubnetId }
        }
      }
    ]
    frontendIPConfigurations: [
      {
        name: 'frontendPublic'
        properties: {
          publicIPAddress: { id: publicIp.id }
        }
      }
    ]
    frontendPorts: [
      {
        name: 'port80'
        properties: { port: 80 }
      }
    ]
    // Left empty on purpose: the scale set registers its instances
    // into this pool, so membership follows autoscaling automatically.
    backendAddressPools: [
      {
        name: 'appBackendPool'
        properties: {}
      }
    ]
    probes: [
      {
        name: 'appHealthProbe'
        properties: {
          protocol: 'Http'
          // Streamlit serves the application at the root path. Newer
          // releases also expose /_stcore/health, which is lighter, but
          // the root path works on every version.
          path: '/'
          interval: 30
          timeout: 30
          unhealthyThreshold: 3
          pickHostNameFromBackendHttpSettings: true
          match: {
            statusCodes: [ '200-399' ]
          }
        }
      }
    ]
    backendHttpSettingsCollection: [
      {
        name: 'appHttpSettings'
        properties: {
          port: appPort
          protocol: 'Http'
          cookieBasedAffinity: 'Enabled'
          // Streamlit keeps session state in memory on the instance that
          // served the first request, so a user must stay on that
          // instance for the whole session. Cookie affinity does that.
          affinityCookieName: 'HotelAppAffinity'
          requestTimeout: 120
          pickHostNameFromBackendAddress: false
          probe: {
            id: resourceId('Microsoft.Network/applicationGateways/probes', gatewayName, 'appHealthProbe')
          }
        }
      }
    ]
    httpListeners: [
      {
        name: 'httpListener'
        properties: {
          frontendIPConfiguration: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendIPConfigurations', gatewayName, 'frontendPublic')
          }
          frontendPort: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendPorts', gatewayName, 'port80')
          }
          protocol: 'Http'
          requireServerNameIndication: false
        }
      }
    ]
    requestRoutingRules: [
      {
        name: 'routeToApp'
        properties: {
          ruleType: 'Basic'
          priority: 100
          httpListener: {
            id: resourceId('Microsoft.Network/applicationGateways/httpListeners', gatewayName, 'httpListener')
          }
          backendAddressPool: {
            id: resourceId('Microsoft.Network/applicationGateways/backendAddressPools', gatewayName, 'appBackendPool')
          }
          backendHttpSettings: {
            id: resourceId('Microsoft.Network/applicationGateways/backendHttpSettingsCollection', gatewayName, 'appHttpSettings')
          }
        }
      }
    ]
  }
}

output gatewayName string = appGateway.name
output backendPoolId string = '${appGateway.id}/backendAddressPools/appBackendPool'
output publicIpAddress string = publicIp.properties.ipAddress
output publicFqdn string = publicIp.properties.dnsSettings.fqdn
