@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('Name of the Storage account')
param aiServiceName string

@allowed([
  'Standard_LRS'
  'Standard_GRS'
  'Standard_RAGRS'
  'Standard_ZRS'
])
@description('Storage SKU')
param aiServiceSkuName string = 'Standard_LRS'

var storageNameCleaned = toLower(replace(aiServiceName, '-', ''))
// Storage account names must be between 3-24 chars and alphanumeric lowercase
// Ensure the passed name meets these constraints or implement truncation if needed.

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: take(storageNameCleaned, 24)
  location: location
  sku: {
    name: aiServiceSkuName
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
    defaultToOAuthAuthentication: true
  }
  tags: tags
}

// Blob service resource under the storage account
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

// Default container under the blob service
resource defaultContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'default'
  properties: {}
}

resource preAuthPoliciesContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'pre-auth-policies'
  properties: {}
}

var storageKeys = storageAccount.listKeys()
var primaryKey = storageKeys.keys[0].value
var storageAccountPrimaryConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${primaryKey};EndpointSuffix=core.windows.net'

output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
output storageAccountPrimaryKey string = primaryKey
output storageAccountPrimaryConnectionString string = storageAccountPrimaryConnectionString
