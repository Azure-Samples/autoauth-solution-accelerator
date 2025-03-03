@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('Name of the AI Foundry instance')
param aiFoundryName string

@description('Display name for the AI Foundry instance')
param aiFoundryFriendlyName string = aiFoundryName

@description('Description for the AI Foundry instance')
param aiFoundryDescription string

@description('Resource ID of the Application Insights resource for diagnostics logs')
param applicationInsightsId string

@description('Resource ID of the Container Registry for storing docker images')
param containerRegistryId string

@description('Resource ID of the Key Vault for storing connection strings')
param keyVaultId string

@description('Resource ID of the Storage Account for experimentation outputs')
param storageAccountId string

@description('Resource ID of the AI Services resource')
param aiServicesId string

@description('Target endpoint of the AI Services')
param aiServicesTarget string

@description('Name of the AI Foundry project')
param aiFoundryProjectName string = 'evaluations'

// Get the storage account name from its resource ID
var storageAccountName = last(split(storageAccountId, '/'))

// Reference the existing storage account
resource existingStorageAccount 'Microsoft.Storage/storageAccounts@2021-04-01' existing = {
  name: storageAccountName
}

// Create the AI Foundry instance (ML workspace with kind "foundry")
resource aiFoundry 'Microsoft.MachineLearningServices/workspaces@2023-08-01-preview' = {
  name: aiFoundryName
  location: location
  tags: tags
  kind: 'foundry'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: aiFoundryFriendlyName
    description: aiFoundryDescription
    keyVault: keyVaultId
    storageAccount: storageAccountId
    applicationInsights: applicationInsightsId
    containerRegistry: containerRegistryId
  }
}

// Create the AI Foundry project as a child resource of the AI Foundry instance
resource aiFoundryProject 'Microsoft.MachineLearningServices/workspaces/projects@2023-08-01-preview' = {
  name: aiFoundryProjectName
  parent: aiFoundry
  properties: {
    displayName: aiFoundryProjectName
    description: 'AI Foundry project for evaluations'
  }
}

// Create a nested connection to the AI Services resource
resource aiServicesConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-01-01-preview' = {
  name: '${aiFoundryName}-connection-AzureOpenAI'
  parent: aiFoundry
  properties: {
    category: 'AzureOpenAI'
    target: aiServicesTarget
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: {
      key: '${listKeys(aiServicesId, '2021-10-01').key1}'
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: aiServicesId
    }
  }
}

// Grant the Storage Blob Data Contributor role to the AI Foundry managed identity on the storage account
resource uaiStorageBlobContrib 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: existingStorageAccount
  name: guid(existingStorageAccount.name, aiFoundryName, 'Storage Blob Data Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: aiFoundry.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

var discoveryHost = replace(replace(aiFoundry.properties.discoveryUrl, 'https://', ''), '/discovery', '')
var subscriptionId = subscription().subscriptionId
var resourceGroupName = toLower(resourceGroup().name)
var connectionString = '${discoveryHost};${subscriptionId};${resourceGroupName};${aiFoundryProjectName}'

output aiFoundryId string = aiFoundry.id
output aiFoundryPrincipalId string = aiFoundry.identity.principalId
output aiFoundryConnectionString string = connectionString
