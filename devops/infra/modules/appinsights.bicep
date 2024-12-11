@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('Name of the Application Insights resource')
param aiServiceName string

var appInsightsNameCleaned = replace(aiServiceName, '-', '')

resource appInsights 'microsoft.insights/components@2020-02-02' = {
  name: appInsightsNameCleaned
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
  tags: tags
}

output appInsightsId string = appInsights.id
output appInsightsName string = appInsights.name
output appInsightsConnectionString string = appInsights.properties.ConnectionString
