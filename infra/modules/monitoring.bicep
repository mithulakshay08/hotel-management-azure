// ============================================================
//  Azure Monitor: Log Analytics workspace plus two alert rules
// ============================================================

@description('Azure region.')
param location string

@description('Prefix applied to every resource name.')
param prefix string

@description('Resource id of the scale set to watch.')
param scaleSetId string

@description('Email address that receives alert notifications.')
param alertEmail string

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    // 30 days is the free allowance; raising it adds cost.
    retentionInDays: 30
  }
}

// Where alerts are delivered.
resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: '${prefix}-oncall'
  location: 'global'
  properties: {
    groupShortName: 'hotelops'
    enabled: true
    emailReceivers: [
      {
        name: 'opsEmail'
        emailAddress: alertEmail
        useCommonAlertSchema: true
      }
    ]
  }
}

// Fires when the scale set is working hard for a sustained period.
// This is the signal that the autoscale rules should already be acting on;
// the alert exists so a human also finds out.
resource cpuAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${prefix}-alert-high-cpu'
  location: 'global'
  properties: {
    description: 'Scale set CPU above 80 percent for 10 minutes.'
    severity: 2
    enabled: true
    scopes: [ scaleSetId ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT10M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'HighCpu'
          metricNamespace: 'Microsoft.Compute/virtualMachineScaleSets'
          metricName: 'Percentage CPU'
          operator: 'GreaterThan'
          threshold: 80
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [
      { actionGroupId: actionGroup.id }
    ]
  }
}

output workspaceId string = workspace.id
output workspaceName string = workspace.name
output actionGroupId string = actionGroup.id
