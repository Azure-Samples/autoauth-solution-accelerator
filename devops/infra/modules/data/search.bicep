@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('Name of the Search service')
param aiServiceName string

@allowed([
  'basic'
])
@description('Search service SKU')
param aiServiceSkuName string = 'basic'

var searchNameCleaned = replace(aiServiceName, '-', '')

resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchNameCleaned
  location: location
  sku: {
    name: aiServiceSkuName
  }
  properties: {
    publicNetworkAccess: 'Enabled'
    hostingMode: 'default'
  }
  tags: tags
}

var searchKeys = searchService.listAdminKeys()

output searchServiceId string = searchService.id
output searchServiceName string = searchService.name
output searchServicePrimaryKey string = searchKeys.primaryKey
output searchServiceEndpoint string = 'https://${searchService.name}.search.windows.net'
