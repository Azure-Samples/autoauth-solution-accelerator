/*  Module: functionapp.bicep
    Deploys an Azure Function App (Python, Flex Consumption)
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

@description('Storage account resource ID for Function App runtime')
param storageAccountResourceId string

// AzureWebJobsStorage via managed identity (no connection string needed for Flex Consumption)
var storageAccountResourceIdForBlobService = '${storageAccountResourceId}'

// App Service Plan — Flex Consumption (FC1)
resource hostingPlan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: '${functionAppName}-plan'
  location: location
  tags: tags
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
  }
  properties: {
    reserved: true // Linux
  }
}

// Build the combined app settings array
var baseSettings = [
  { name: 'AzureWebJobsStorage__accountName', value: storageAccountName }
  { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: applicationInsightsConnectionString }
  { name: 'AZURE_CLIENT_ID', value: userAssignedIdentityClientId }
]

var allSettings = concat(baseSettings, appSettings)

// Function App — Flex Consumption
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
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${reference(storageAccountResourceIdForBlobService, '2023-05-01').primaryEndpoints.blob}deploymentpackages'
          authentication: {
            type: 'UserAssignedIdentity'
            userAssignedIdentityResourceId: userAssignedIdentityResourceId
          }
        }
      }
      runtime: {
        name: 'python'
        version: '3.11'
      }
      scaleAndConcurrency: {
        maximumInstanceCount: 100
        instanceMemoryMB: 2048
      }
    }
    httpsOnly: true
  }
}

// Deployment package blob container
resource storageAccountRef 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = {
  parent: storageAccountRef
  name: 'default'
}

resource deploymentContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'deploymentpackages'
  properties: {
    publicAccess: 'None'
  }
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

// Grant Storage Queue Data Contributor for AzureWebJobsStorage queue operations (required for Flex Consumption)
resource storageQueueDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccountRef
  name: guid(storageAccountRef.id, functionAppName, 'Storage Queue Data Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88')
    principalId: reference(userAssignedIdentityResourceId, '2023-01-31').principalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Storage Table Data Contributor for AzureWebJobsStorage table operations (required for Flex Consumption)
resource storageTableDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storageAccountRef
  name: guid(storageAccountRef.id, functionAppName, 'Storage Table Data Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
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
