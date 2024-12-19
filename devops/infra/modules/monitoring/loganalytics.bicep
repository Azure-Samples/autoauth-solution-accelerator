@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('Name of the Log Analytics Workspace')
param logAnalyticsName string

var logAnalyticsCleaned = replace(logAnalyticsName, '-', '')

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2020-08-01' = {
  name: logAnalyticsCleaned
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    workspaceCapping: {}
  }
  dependsOn: []
}

output logAnalyticsId string = logAnalytics.id
output logAnalyticsName string = logAnalytics.name
