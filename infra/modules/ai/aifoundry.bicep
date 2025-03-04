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

@description('API key for the AI Services resource')
param aiServicesKey string

@description('Target endpoint of the AI Services')
param aiServicesTarget string

@description('Name of the AI Foundry project (evaluations)')
param aiFoundryProjectName string = 'evaluations'

// Extract the storage account name from its resource ID
var storageAccountName = last(split(storageAccountId, '/'))

// Reference the existing storage account
resource existingStorageAccount 'Microsoft.Storage/storageAccounts@2021-04-01' existing = {
  name: storageAccountName
}

// // Reference the existing blob service (always named 'default')
// resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2021-02-01' existing = {
//   parent: existingStorageAccount
//   name: 'default'
// }

// // Create the artifact container in the existing storage account
// resource artifactContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-02-01' = {
//   parent: blobService
//   name: '${aiFoundryProjectName}-artifactstore'
//   properties: {
//     publicAccess: 'None'
//   }
// }

// // Create the blob container in the existing storage account
// resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-02-01' = {
//   parent: blobService
//   name: '${aiFoundryProjectName}-blobstore'
//   properties: {
//     publicAccess: 'None'
//   }
// }

// // Reference the existing file service (always named 'default')
// resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' existing = {
//   parent: existingStorageAccount
//   name: 'default'
// }

// // Create the file share for the working directory in the existing storage account
// resource workingFileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
//   parent: fileService
//   name: '${aiFoundryProjectName}-workingdirectory'
//   properties: {
//     accessTier: 'TransactionOptimized'
//     shareQuota: 102400
//     enabledProtocols: 'SMB'
//   }
// }

// Create the AI Foundry instance (ML workspace with kind "hub")
resource aiFoundry 'Microsoft.MachineLearningServices/workspaces@2023-08-01-preview' = {
  name: aiFoundryName
  location: location
  tags: tags
  kind: 'hub'
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

// Create the AI Foundry project (ML workspace with kind "Project")
resource aiFoundryProject 'Microsoft.MachineLearningServices/workspaces@2024-04-01-preview' = {
  name: aiFoundryProjectName
  location: location
  tags: tags
  kind: 'Project'
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    hubResourceId: aiFoundry.id
    description: 'AI Foundry project for evaluations'
    systemDatastoresAuthMode: 'identity'
    discoveryUrl: 'https://${location}.api.azureml.ms/discovery'
  }
}

// Create a nested connection to the AI Services resource under the hub using managed identity
resource aiServicesConnection 'Microsoft.MachineLearningServices/workspaces/connections@2024-07-01-preview' = {
  name: '${aiFoundryName}-connection-AzureOpenAI'
  parent: aiFoundry
  properties: {
    category: 'AzureOpenAI'
    target: aiServicesTarget
    authType: 'ApiKey'
    useWorkspaceManagedIdentity: true
    isSharedToAll: true
    sharedUserList: []
    peRequirement: 'NotRequired'
    peStatus: 'NotApplicable'
    credentials: {
      key: aiServicesKey
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: aiServicesId
      ApiVersion: '2023-07-01-preview'
      DeploymentApiVersion: '2023-10-01-preview'
    }
  }
}

// // Grant the Storage Blob Data Contributor role on the storage account to the AI Foundry managed identity
// resource uaiStorageBlobContrib 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
//   scope: existingStorageAccount
//   name: guid(existingStorageAccount.name, aiFoundryName, 'Storage Blob Data Contributor')
//   properties: {
//     roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
//     principalId: aiFoundry.identity.principalId
//     principalType: 'ServicePrincipal'
//   }
// }

resource uaiStorageFileContrib 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: existingStorageAccount
  name: guid(existingStorageAccount.name, aiFoundryName, 'Storage File Data SMB Share Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0c867c2a-1d8c-454a-a3db-ab2ea1bdc8bb')
    principalId: aiFoundry.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource uaiProjectStorageFileContrib 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: existingStorageAccount
  name: guid(existingStorageAccount.name, aiFoundryProjectName, 'Storage File Data SMB Share Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0c867c2a-1d8c-454a-a3db-ab2ea1bdc8bb')
    principalId: aiFoundryProject.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// // Datastore for workspace artifact store – using no service identity for data access
// resource workspaceArtifactStore 'Microsoft.MachineLearningServices/workspaces/datastores@2024-07-01-preview' = {
//   name: '${aiFoundryProjectName}_workspaceartifactstore'
//   parent: aiFoundryProject
//   dependsOn: [
//     uaiProjectStorageFileContrib
//     uaiStorageFileContrib
//   ]
//   properties: {
//     credentials: {
//       credentialsType: 'None'
//     }
//     datastoreType: 'AzureBlob'
//     accountName: storageAccountName
//     containerName: '${aiFoundryProjectName}-artifactstore'
//     endpoint: environment().suffixes.storage
//     protocol: 'https'
//     serviceDataAccessAuthIdentity: 'WorkspaceSystemAssignedIdentity'
//   }
// }

// // Datastore for workspace blob store – using the workspace system-assigned identity
// resource workspaceBlobStore 'Microsoft.MachineLearningServices/workspaces/datastores@2024-07-01-preview' = {
//   name: '${aiFoundryProjectName}_workspaceblobstore'
//   parent: aiFoundryProject
//   dependsOn: [
//     uaiProjectStorageFileContrib
//     uaiStorageFileContrib
//   ]
//   properties: {
//     credentials: {
//       credentialsType: 'None'
//     }
//     datastoreType: 'AzureBlob'
//     subscriptionId: subscription().subscriptionId
//     resourceGroup: resourceGroup().name
//     accountName: storageAccountName
//     containerName: '${aiFoundryProjectName}-blobstore'
//     endpoint: environment().suffixes.storage
//     protocol: 'https'
//     serviceDataAccessAuthIdentity: 'WorkspaceSystemAssignedIdentity'
//   }
// }

// resource workspaceWorkingDirectory 'Microsoft.MachineLearningServices/workspaces/datastores@2024-07-01-preview' = {
//   name: '${aiFoundryProjectName}_workspaceworkingdirectory'
//   parent: aiFoundryProject
//   dependsOn: [
//     uaiProjectStorageFileContrib
//     uaiStorageFileContrib
//     workingFileShare
//   ]
//   properties: {
//     credentials: {
//       credentialsType: 'None'
//     }
//     datastoreType: 'AzureFile'
//     accountName: storageAccountName
//     fileShareName: '${aiFoundryProjectName}-workingdirectory'
//     endpoint: environment().suffixes.storage
//     protocol: 'https'
//     serviceDataAccessAuthIdentity: 'None'
//   }
// }

// Build a connection string using the project discovery URL
var discoveryHost = replace(replace(aiFoundryProject.properties.discoveryUrl, 'https://', ''), '/discovery', '')
var subscriptionId = subscription().subscriptionId
var resourceGroupName = toLower(resourceGroup().name)
var connectionString = '${discoveryHost};${subscriptionId};${resourceGroupName};${aiFoundryProjectName}'

output aiFoundryId string = aiFoundry.id
output aiFoundryPrincipalId string = aiFoundry.identity.principalId
output aiFoundryConnectionString string = connectionString
