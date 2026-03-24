/*  Module: functionapp.bicep
    Deploys an Azure Function App (Python, Elastic Premium)
    for the policy indexer service.
*/

@description('Name for the Function App')
param functionAppName string

@description('Location for all resources')
param location string = resourceGroup().location

@description('Tags to apply to resources')
param tags object = {}

@description('Application Insights connection string for monitoring')
param applicationInsightsConnectionString string

@description('Resource ID of the user-assigned managed identity')
param userAssignedIdentityResourceId string

@description('Client ID of the user-assigned managed identity')
param userAssignedIdentityClientId string

@description('App settings (environment variables) for the Function App')
param appSettings array = []

@description('Storage account name for the Function App runtime')
param storageAccountName string

@secure()
@description('Storage account connection string for the content share (required by Elastic Premium ARM provider)')
param storageAccountConnectionString string

@description('Additional CORS origins to allow for the Function App')
param allowedCorsOrigins array = [
  'https://portal.azure.com'
]

// App Service Plan — Elastic Premium (EP1)
resource hostingPlan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: '${functionAppName}-plan'
  location: location
  tags: tags
  sku: {
    name: 'EP1'
    tier: 'ElasticPremium'
  }
  properties: {
    reserved: true // Linux
    maximumElasticWorkerCount: 20
  }
}

// Build the combined app settings array
// AzureWebJobsStorage uses connection string (required by EP ARM provider for storage validation).
// WEBSITE_CONTENTAZUREFILECONNECTIONSTRING is required by EP for the Azure Files content share.
// Application-level operations (blob triggers, search, doc intelligence) use managed identity via AZURE_CLIENT_ID.
var baseSettings = [
  { name: 'AzureWebJobsStorage', value: storageAccountConnectionString }
  { name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING', value: storageAccountConnectionString }
  { name: 'WEBSITE_CONTENTSHARE', value: functionAppName }
  { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
  { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
  { name: 'SCM_DO_BUILD_DURING_DEPLOYMENT', value: 'true' }
  { name: 'ENABLE_ORYX_BUILD', value: 'true' }
  { name: 'PYTHON_ISOLATE_WORKER_DEPENDENCIES', value: '1' }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: applicationInsightsConnectionString }
  { name: 'AZURE_CLIENT_ID', value: userAssignedIdentityClientId }
]

var allSettings = concat(baseSettings, appSettings)

// Function App — Elastic Premium
resource functionApp 'Microsoft.Web/sites@2024-04-01' = {
  name: functionAppName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityResourceId}': {}
    }
  }
  properties: {
    serverFarmId: hostingPlan.id
    reserved: true
    siteConfig: {
      appSettings: allSettings
      cors: {
        allowedOrigins: allowedCorsOrigins
      }
      linuxFxVersion: 'PYTHON|3.11'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
    httpsOnly: true
  }
}

resource storageAccountRef 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

// Grant the managed identity Storage Blob Data Contributor on the storage account
// so it can read deployment packages and manage AzureWebJobsStorage
resource storageBlobDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccountRef
  name: guid(storageAccountRef.id, functionAppName, 'Storage Blob Data Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: reference(userAssignedIdentityResourceId, '2023-01-31').principalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Storage Account Contributor for AzureWebJobsStorage internal operations
resource storageAccountContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccountRef
  name: guid(storageAccountRef.id, functionAppName, 'Storage Account Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '17d1049b-9a84-46fb-8f53-869881c3d3ab')
    principalId: reference(userAssignedIdentityResourceId, '2023-01-31').principalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Storage Queue Data Contributor for AzureWebJobsStorage queue operations
resource storageQueueDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccountRef
  name: guid(storageAccountRef.id, functionAppName, 'Storage Queue Data Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88')
    principalId: reference(userAssignedIdentityResourceId, '2023-01-31').principalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Storage Table Data Contributor for AzureWebJobsStorage table operations
resource storageTableDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccountRef
  name: guid(storageAccountRef.id, functionAppName, 'Storage Table Data Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
    principalId: reference(userAssignedIdentityResourceId, '2023-01-31').principalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Storage File Data Privileged Contributor for Azure Files content share (required for Elastic Premium with RBAC)
resource storageFileDataPrivilegedContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccountRef
  name: guid(storageAccountRef.id, functionAppName, 'Storage File Data Privileged Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '69566ab7-960f-475b-8e7c-b3118f30c6bd')
    principalId: reference(userAssignedIdentityResourceId, '2023-01-31').principalId
    principalType: 'ServicePrincipal'
  }
}

@description('Name of the deployed Function App')
output functionAppName string = functionApp.name

@description('Default hostname of the Function App')
output functionAppHostname string = functionApp.properties.defaultHostName

@description('Resource ID of the Function App')
output functionAppResourceId string = functionApp.id
