/*  Module: resources.bicep
  This Bicep file deploys a set of Azure resources for a “Prior Authorization” scenario.
  It includes the deployment of AI services, container apps, storage, Cosmos DB, and monitoring.
  The file also sets up user-assigned identities, manages role assignments, and configures
  environment variables for containerized applications.

  Services used:
  - AI Services: OpenAI, Document Intelligence, Multi-Account AI Services
  - Container Apps: Frontend and Backend container apps, Container registry
  - Storage: Azure Storage Account
  - Database: Cosmos DB (MongoDB API)
  - Monitoring: Azure Monitor, Log Analytics, Application Insights
  - Identity: User-assigned Managed Identity
  - Role Assignments: Various role assignments for accessing resources
*/

// Managed by AZD - Flag for handling of mapping the deployed image to the container app:
param frontendExists bool = false
param backendExists bool = false
// ----------------------------------------------------------------------------------------
@description('Flag to indicate if EasyAuth should be enabled for the Container Apps (Defaults to true)')
param enableEasyAuth bool

@description('Flag to indicate if the Container App should be deployed with ingress disabled')
param disableIngress bool

// Execute this main file to deploy Prior Authorization related resources in a basic configuration
@minLength(2)
@maxLength(12)
@description('Name for the PriorAuth resource and used to derive the name of dependent resources.')
param priorAuthName string = 'priorAuth'

@description('Set of tags to apply to all resources.')
param tags object = {}

@description('API Version of the OpenAI API')
param openaiApiVersion string

// @description('Admin password for the cluster')
// @secure()
// param cosmosAdministratorPassword string

param cosmosDbCollectionName string = 'temp'
param cosmosDbDatabaseName string = 'priorauthsessions'

param reasoningModel object

param chatModel object

param embeddingModel object

// Create an array of models for the OpenAI service deployment
var chatCompletionModels = [
  chatModel
  reasoningModel
]

param gitHash string = ''

@description('Embedding model size for the OpenAI Embedding deployment')
param embeddingModelDimension string

@description('Storage Blob Container name to land the files for Prior Auth')
param storageBlobContainerName string = 'default'

var name = toLower('${priorAuthName}')
var uniqueSuffix = substring(uniqueString(resourceGroup().id), 0, 7)
var storageServiceName = toLower(replace('storage-${name}-${uniqueSuffix}', '-', ''))
var location = resourceGroup().location

// @TODO: Replace with AVM module; consolidate into AI Service
module docIntelligence 'modules/ai/docintelligence.bicep' = {
  name: 'doc-intelligence-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'doc-intelligence-${name}-${uniqueSuffix}'
    location: location
    tags: tags
    aiServiceSkuName: 'S0'
  }
}

// @TODO: Replace with AVM module
module multiAccountAiServices 'modules/ai/mais.bicep' = {
  name: 'multiservice-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'multiservice-${name}-${uniqueSuffix}'
    location: location
    tags: tags
    aiServiceSkuName: 'S0' // or another allowed SKU if appropriate
  }
}

// @TODO: Replace with AVM module
module openAiService 'modules/ai/openai.bicep' = {
  name: 'openai-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'openai-${name}-${uniqueSuffix}'
    location: location
    tags: tags
    aiServiceSkuName: 'S0'
    embeddingModel: embeddingModel
    chatCompletionModels: chatCompletionModels
  }
}

// @TODO: Replace with AVM module
module searchService 'modules/data/search.bicep' = {
  name: 'search-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'search-${name}-${uniqueSuffix}'
    location: location
    tags: tags
    aiServiceSkuName: 'basic'
  }
}

resource searchStorageBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: resourceGroup()
  name: guid(storageAccount.name, searchService.name, 'Storage Blob Data Reader')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1') // Storage Blob Data Reader
    principalId: searchService.outputs.searchServiceIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// @TODO: Replace with AVM module
module storageAccount 'modules/data/storage.bicep' = {
  name: 'storage-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: storageServiceName
    location: location
    tags: tags
    aiServiceSkuName: 'Standard_LRS'
  }
}

// @TODO: Replace with AVM module
module cosmosDb 'modules/data/cosmos-mongo-ru.bicep' = {
  name: 'cosmosdb-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'cosmosdb-${name}-${uniqueSuffix}'
    location: location
    tags: tags
  }
}

// Monitor application with Azure Monitor
module monitoring 'br/public:avm/ptn/azd/monitoring:0.1.0' = {
  name: 'avm-monitoring-${name}-${uniqueSuffix}-deployment'
  params: {
    logAnalyticsName: 'loganalytics-${name}-${uniqueSuffix}'
    applicationInsightsName: 'appinsights-${name}-${uniqueSuffix}'
    applicationInsightsDashboardName: 'aiDashboard-${name}-${uniqueSuffix}'
    location: location
    tags: tags
  }
}

module vault 'br/public:avm/res/key-vault/vault:0.12.1' = {
  name: 'vault-${name}-${uniqueSuffix}-deployment'
  params: {
    // Required parameter: name for the vault
    name: 'kv-${name}-${uniqueSuffix}'
    // Non-required parameter
    enablePurgeProtection: false
  }
}

module aiFoundry 'modules/ai/aifoundry.bicep' = {
  name: 'ai-foundry-${name}-${uniqueSuffix}-deployment'
  params: {
    aiFoundryName: 'ai-foundry-${name}-${uniqueSuffix}'
    aiFoundryFriendlyName: 'AI Foundry - ${name}'
    aiFoundryDescription: 'AI Foundry instance for the Prior Authorization scenario'
    applicationInsightsId: monitoring.outputs.applicationInsightsResourceId
    containerRegistryId: registry.outputs.resourceId
    keyVaultId: vault.outputs.resourceId
    storageAccountId: storageAccount.outputs.storageAccountId
    aiServicesId: openAiService.outputs.aiServicesId
    aiServicesKey: openAiService.outputs.aiServicesKey
    aiServicesTarget: openAiService.outputs.aiServicesEndpoint
    tags: tags
    location: location
  }
}

module appIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.2.1' = {
  name: 'uai-app-${name}-${uniqueSuffix}-deployment'
  params: {
    name: 'uai-app-${name}-${uniqueSuffix}'
    location: location
  }
}

// Grant Role Assignments for the User Assigned App Identity to communicate with the storage account
resource uaiStorageBlobContrib 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: resourceGroup()
  name: guid(storageAccount.name, appIdentity.name, 'Storage Blob Data Contributor')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalId: appIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

resource uaiStorageBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: resourceGroup()
  name: guid(storageAccount.name, appIdentity.name, 'Storage Blob Data Reader')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1') // Storage Blob Data Reader
    principalId: appIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

resource aiFoundryWorkspaceReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiFoundry.name, appIdentity.name, 'Azure AI Developer')
  scope: resourceGroup()
  properties: {
    principalId: appIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '64702f94-c441-49e6-a78b-ef80e0188fee') // Contributor Role ID
  }
}

/**
 * Container related configurations start here.
 */
module registry 'br/public:avm/res/container-registry/registry:0.1.1' = {
  name: 'avm-registry-${name}-${uniqueSuffix}-deployment'
  params: {
    name: toLower(replace('registry-${name}-${uniqueSuffix}', '-', ''))
    acrAdminUserEnabled: false
    publicNetworkAccess: 'Enabled'
    location: location
    tags: tags
    roleAssignments: [
      {
        principalId: appIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
      }
    ]
  }
}

var storageConnString = 'ResourceId=${storageAccount.outputs.storageAccountId}'


var containerEnvArray = [
  {
    name: 'AZURE_CLIENT_ID'
    value: appIdentity.outputs.clientId
  }
  {
    name: 'AZURE_OPENAI_ENDPOINT'
    value: openAiService.outputs.aiServicesEndpoint
  }
  {
    name: 'AZURE_OPENAI_API_VERSION'
    value: openaiApiVersion
  }
  {
    name: 'AZURE_OPENAI_API_VERSION_01'
    value: contains(reasoningModel.name, 'o1') || contains(reasoningModel.name, 'o3') ? openaiApiVersion : ''
  }
  {
    name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
    value: embeddingModel.name
  }
  {
    name: 'AZURE_OPENAI_CHAT_DEPLOYMENT_ID'
    value: chatModel.name
  }
  {
    name: 'AZURE_OPENAI_CHAT_DEPLOYMENT_01'
    value: contains(reasoningModel.name, 'o1') || contains(reasoningModel.name, 'o3') ? reasoningModel.name : ''
  }
  {
    name: 'AZURE_OPENAI_EMBEDDING_DIMENSIONS'
    value: embeddingModelDimension
  }
  {
    name: 'AZURE_SEARCH_SERVICE_NAME'
    value: searchService.outputs.searchServiceName
  }
  {
    name: 'AZURE_SEARCH_INDEX_NAME'
    value: 'ai-policies-index'
  }
  {
    name: 'AZURE_AI_SEARCH_SERVICE_ENDPOINT'
    value: searchService.outputs.searchServiceEndpoint
  }
  {
    name: 'AZURE_BLOB_CONTAINER_NAME'
    value: storageBlobContainerName
  }
  {
    name: 'AZURE_STORAGE_ACCOUNT_NAME'
    value: storageAccount.outputs.storageAccountName
  }
  {
    name: 'AZURE_COSMOS_DB_DATABASE_NAME'
    value: cosmosDbDatabaseName
  }
  {
    name: 'AZURE_COSMOS_DB_COLLECTION_NAME'
    value: cosmosDbCollectionName
  }
  {
    name: 'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT'
    value: docIntelligence.outputs.aiServicesEndpoint
  }
  {
    name: 'AZURE_OPENAI_KEY'
    value: openAiService.outputs.aiServicesKey
  }
  {
    name: 'AZURE_AI_SEARCH_ADMIN_KEY'
    value: searchService.outputs.searchServicePrimaryKey
  }
  {
    name: 'AZURE_STORAGE_CONNECTION_STRING'
    value: storageConnString
  }
  {
    name: 'AZURE_AI_SERVICES_KEY'
    value: multiAccountAiServices.outputs.aiServicesPrimaryKey
  }
  {
    name: 'AZURE_COSMOS_CONNECTION_STRING'
    value: cosmosDb.outputs.mongoConnectionString
  }
  {
    name: 'AZURE_DOCUMENT_INTELLIGENCE_KEY'
    value: docIntelligence.outputs.aiServicesKey
  }
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: monitoring.outputs.applicationInsightsConnectionString
  }
  {
    name: 'AZURE_AI_FOUNDRY_CONNECTION_STRING'
    value: aiFoundry.outputs.aiFoundryConnectionString
  }
  {
    name: 'GIT_HASH'
    value: gitHash
  }
]

module containerAppsEnvironment 'br/public:avm/res/app/managed-environment:0.8.1' = {
  name: 'managedenv-${name}-${uniqueSuffix}-deployment'
  params: {
    // Required parameters
    logAnalyticsWorkspaceResourceId: monitoring.outputs.logAnalyticsWorkspaceResourceId
    name: toLower('managedEnv-${name}-${uniqueSuffix}')
    // Non-required parameters
    location: location
    zoneRedundant: false
    appInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
    openTelemetryConfiguration: {
      logsConfiguration: {
        destinations: [
          'appInsights'
        ]
      }
      tracesConfiguration: {
        destinations: [
          'appInsights'
        ]
      }
    }

    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

var frontendContainerName = toLower('pe-fe-${name}-${uniqueSuffix}')
var backendContainerName = toLower('pe-be-${name}-${uniqueSuffix}')

var registries = [
  {
    identity: appIdentity.outputs.resourceId
    server: registry.outputs.loginServer
  }
]

// AZD-supporting modules - Fetch the latest image from the container registry if AZD has deployed the image and set the
//   service-based environment variable flag (SERVICE_{SERVICE_NAME}_RESOURCE_EXISTS) to true.
module frontendFetchLatestImage './modules/compute/fetch-container-image.bicep' = {
  name: 'frontend-fetch-image'
  params: {
    exists: frontendExists
    name: frontendContainerName
  }
}

module backendFetchLatestImage './modules/compute/fetch-container-image.bicep' = {
  name: 'backend-fetch-image'
  params: {
    exists: backendExists
    name: backendContainerName
  }
}

// If the container app exists, use the existing image, otherwise use the default image
var frontendImage = frontendExists
                    ? frontendFetchLatestImage.outputs.containers[0].image
                    : 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

var frontendContainer = {
  name: frontendContainerName
  image: frontendImage
  command: []
  args: []
  resources: {
    cpu: json('2.0')
    memory: '4Gi'
  }
  env: containerEnvArray

}


var jobAppContainer = {
  name: '${backendContainerName}-job'
  image: frontendImage
  command: ['/bin/bash']
  args: ['-c', 'python /app/src/pipeline/policyIndexer/indexerSetup.py --target \'/app\'']
  env: containerEnvArray
}

module frontendContainerApp 'br/public:avm/res/app/container-app:0.13.0' = {
  name: frontendContainerName
  params: {
    // Required parameters
    name: frontendContainerName
    environmentResourceId: containerAppsEnvironment.outputs.resourceId
    containers: [
      frontendContainer
    ]
    stickySessionsAffinity: 'sticky'
    secrets: [
      {
        name: 'override-use-mi-fic-assertion-client-id'
        value: appIdentity.outputs.clientId
      }
    ]
    disableIngress: disableIngress

    // Non-required parameters
    scaleMinReplicas: 1
    scaleMaxReplicas: 3

    ingressTargetPort: 8501 // See Dockerfile

    registries: registries
    managedIdentities: {
      userAssignedResourceIds:[
        appIdentity.outputs.resourceId
      ]
    }
    workloadProfileName: 'Consumption'
    location: location
    tags: union(tags, { 'azd-service-name': 'frontend' })
  }
}

module indexInitializationJob 'br/public:avm/res/app/job:0.5.1' = {
  name: '${backendContainerName}-job'
  params: {
    // Required parameters
    containers: [
      jobAppContainer
    ]
    environmentResourceId: containerAppsEnvironment.outputs.resourceId
    name: '${backendContainerName}-job'
    triggerType: 'Manual'

    // Non-required parameters
    registries: registries
    manualTriggerConfig: {
      parallelism: 1
      replicaCompletionCount: 1
    }
    replicaTimeout: 1000
    replicaRetryLimit: 3
    managedIdentities: {
      userAssignedResourceIds:[
        appIdentity.outputs.resourceId
      ]
    }
    roleAssignments: [
      {
        name: guid('${backendContainerName}-job', 'Container App Jobs Operator')
        principalId: appIdentity.outputs.principalId
        principalType: 'ServicePrincipal'
        roleDefinitionIdOrName: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b9a307c4-5aa3-4b52-ba60-2b17c136cd7b') // Container App Job Contributor
      }
    ]
    location: location
  }
}

// ----------------------------------------------------------------------------------------
// Enabling EasyAuth for the ContainerApps
// ----------------------------------------------------------------------------------------
var issuer = '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'
module easyAuthAppReg './modules/security/appregistration.bicep' = if (enableEasyAuth) {
  name: 'easyauth-reg'
  params: {
    clientAppName: '${priorAuthName}-${uniqueSuffix}-easyauth-client-app'
    clientAppDisplayName: '${priorAuthName}-${uniqueSuffix}-EasyAuth-app'
    webAppEndpoint: 'https://${frontendContainerApp.outputs.fqdn}'
    webAppIdentityId: appIdentity.outputs.principalId
    issuer: issuer
    // serviceManagementReference: serviceManagementReference
  }
}

module feAppUpdate './modules/security/appupdate.bicep' = if (enableEasyAuth) {
  name: 'easyauth-frontend-appupdate'
  params: {
    containerAppName: frontendContainerApp.outputs.name
    clientId: easyAuthAppReg.outputs.clientAppId
    openIdIssuer: issuer
    // includeTokenStore: includeTokenStore
    // appIdentityResourceId: includeTokenStore ? aca.outputs.identityResourceId : ''
  }
}

output AZURE_OPENAI_ENDPOINT string = openAiService.outputs.aiServicesEndpoint
output AZURE_OPENAI_API_VERSION string = chatModel.version
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = embeddingModel.name
output AZURE_OPENAI_CHAT_DEPLOYMENT_ID string = chatCompletionModels[0].name
output AZURE_OPENAI_CHAT_DEPLOYMENT_01 string = contains(reasoningModel.name, 'o1') ? reasoningModel.name : ''
output AZURE_OPENAI_EMBEDDING_DIMENSIONS string = embeddingModelDimension
output AZURE_SEARCH_SERVICE_NAME string = searchService.outputs.searchServiceName
output AZURE_SEARCH_INDEX_NAME string = 'ai-policies-index'
output AZURE_AI_SEARCH_ADMIN_KEY string = searchService.outputs.searchServicePrimaryKey
output AZURE_AI_SEARCH_SERVICE_ENDPOINT string = searchService.outputs.searchServiceEndpoint
output AZURE_STORAGE_ACCOUNT_KEY string = ''
output AZURE_BLOB_CONTAINER_NAME string = storageBlobContainerName
output AZURE_STORAGE_ACCOUNT_NAME string = storageAccount.outputs.storageAccountName
output AZURE_STORAGE_CONNECTION_STRING string = storageConnString
output AZURE_AI_SERVICES_KEY string = multiAccountAiServices.outputs.aiServicesPrimaryKey
output AZURE_COSMOS_DB_DATABASE_NAME string = 'priorauthsessions'

output AZURE_COSMOS_DB_COLLECTION_NAME string = 'temp'
output AZURE_COSMOS_CONNECTION_STRING string = cosmosDb.outputs.mongoConnectionString
output AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT string = docIntelligence.outputs.aiServicesEndpoint
output AZURE_DOCUMENT_INTELLIGENCE_KEY string = docIntelligence.outputs.aiServicesKey
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.applicationInsightsConnectionString
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.outputs.loginServer
output AZURE_CONTAINER_ENVIRONMENT_ID string = containerAppsEnvironment.outputs.resourceId
output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerAppsEnvironment.outputs.name
output AZURE_OPENAI_KEY string = openAiService.outputs.aiServicesKey
output AZURE_AI_FOUNDRY_CONNECTION_STRING string = aiFoundry.outputs.aiFoundryConnectionString
output CONTAINER_JOB_NAME string = indexInitializationJob.outputs.name

output FRONTEND_CONTAINER_URL string = frontendContainerApp.outputs.fqdn
output FRONTEND_CONTAINER_NAME string = frontendContainerApp.outputs.name
// output BACKEND_CONTAINER_URL string = backendContainerApp.outputs.fqdn
// output BACKEND_CONTAINER_NAME string = backendContainerApp.outputs.name
output APP_IDENTITY_CLIENT_ID string = appIdentity.outputs.clientId
output APP_IDENTITY_PRINCIPAL_ID string = appIdentity.outputs.principalId
