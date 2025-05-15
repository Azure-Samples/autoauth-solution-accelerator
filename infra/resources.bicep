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
@description('Flag to indicate if EasyAuth should be enabled for the Container Apps')
param enableEasyAuth bool

@description('Flag to indicate if the Container App should be deployed with ingress disabled')
param disableIngress bool

@description('Flag to indicate if API Management should be enabled for the AI Services')
param enableAPIManagement bool

import { ModelConfig, BackendConfigItem } from './modules/ai/types.bicep'


// Execute this main file to deploy Prior Authorization related resources in a basic configuration
@minLength(2)
@maxLength(12)
@description('Name for the PriorAuth resource and used to derive the name of dependent resources.')
param priorAuthName string = 'priorAuth'

@description('Set of tags to apply to all resources.')
param tags object = {}

@description('API Version of the OpenAI API')
param openAiApiVersion string

@description('Name of the Cosmos DB collection.')
param cosmosDbCollectionName string = 'temp'

@description('Name of the Cosmos DB database.')
param cosmosDbDatabaseName string = 'priorauthsessions'

@description('For when APIM is enabled: Array of backend configurations for the AI services.')
param backendConfig BackendConfigItem[] = []

@description('Object containing the reasoning model configuration for OpenAI.')
param reasoningModel ModelConfig

@description('Object containing the chat model configuration for OpenAI.')
param chatModel ModelConfig

@description('Object containing the embedding model configuration for OpenAI.')
param embeddingModel ModelConfig

@description('Git hash of the deployed code. Used for tracking purposes.')
param gitHash string = ''

@description('Embedding model size for the OpenAI Embedding deployment')
param embeddingModelDimension string

@description('Storage Blob Container name to land the files for Prior Auth')
param storageBlobContainerName string = 'default'

var _name = toLower('${priorAuthName}')
var _uniqueSuffix = substring(uniqueString(resourceGroup().id), 0, 7)
var _storageServiceName = toLower(replace('storage-${_name}-${_uniqueSuffix}', '-', ''))
var _location = resourceGroup().location

module multiAccountAiServices 'modules/ai/mais.bicep' = {
  name: 'multiservice-${_name}-${_uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'multiservice-${_name}-${_uniqueSuffix}'
    location: _location
    tags: tags
    aiServiceSkuName: 'S0' // or another allowed SKU if appropriate
  }
}

// AI Gateway deployment (AI Services, APIM and its related components)
// ===========================================================
module aiGateway 'ai-gateway.bicep' = {
  name: 'ai-gateway-${_name}-${_uniqueSuffix}-deployment'
  params: {
    name: 'ai-gateway-${_name}-${_uniqueSuffix}'
    enableAPIManagement: enableAPIManagement
    location: _location
    tags: tags
    apimSku: 'StandardV2'
    backendConfig: backendConfig
    chatModel: chatModel
    reasoningModel: reasoningModel
    embeddingModel: embeddingModel
  }
}

var _openAiEndpoint = aiGateway.outputs.endpoints.openAI
var _openAiKey = aiGateway.outputs.subscriptionKeys.openAI
var _docIntelligenceEndpoint = aiGateway.outputs.aiServices[0].endpoints.value.documentIntelligence
var _docIntelligenceKey = aiGateway.outputs.aiServices[0].key.value
var _aiServicesIdForFoundry = aiGateway.outputs.aiServicesIds

module searchService 'modules/data/search.bicep' = {
  name: 'search-${_name}-${_uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'search-${_name}-${_uniqueSuffix}'
    location: _location
    tags: tags
    aiServiceSkuName: 'basic'
  }
}

module vault 'br/public:avm/res/key-vault/vault:0.12.1' = {
  name: 'vault-${_name}-${_uniqueSuffix}-deployment'
  params: {
    // Required parameter: name for the vault
    name: 'kv-${_name}-${_uniqueSuffix}'
    // Non-required parameter
    enablePurgeProtection: false

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

module storageAccount 'modules/data/storage.bicep' = {
  name: 'storage-${_name}-${_uniqueSuffix}-deployment'
  params: {
    aiServiceName: _storageServiceName
    location: _location
    tags: tags
    aiServiceSkuName: 'Standard_LRS'
  }
}

module cosmosDb 'modules/data/cosmos-mongo-ru.bicep' = {
  name: 'cosmosdb-${_name}-${_uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'cosmosdb-${_name}-${_uniqueSuffix}'
    location: _location
    tags: tags
  }
}

module monitoring 'br/public:avm/ptn/azd/monitoring:0.1.0' = {
  name: 'avm-monitoring-${_name}-${_uniqueSuffix}-deployment'
  params: {
    logAnalyticsName: 'loganalytics-${_name}-${_uniqueSuffix}'
    applicationInsightsName: 'appinsights-${_name}-${_uniqueSuffix}'
    applicationInsightsDashboardName: 'aiDashboard-${_name}-${_uniqueSuffix}'
    location: _location
    tags: tags
  }
}

module aiFoundry 'modules/ai/aifoundry.bicep' = {
  name: 'ai-foundry-${_name}-${_uniqueSuffix}-deployment'
  params: {
    aiFoundryName: 'ai-foundry-${_name}-${_uniqueSuffix}'
    aiFoundryFriendlyName: 'AI Foundry - ${_name}'
    aiFoundryDescription: 'AI Foundry instance for the Prior Authorization scenario'
    applicationInsightsId: monitoring.outputs.applicationInsightsResourceId
    containerRegistryId: registry.outputs.resourceId
    keyVaultId: vault.outputs.resourceId
    storageAccountId: storageAccount.outputs.storageAccountId
    aiServicesIds: _aiServicesIdForFoundry
    aiServicesKey: _openAiKey
    aiServicesTarget: _openAiEndpoint
    tags: tags
    location: _location
  }
}

module appIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.2.1' = {
  name: 'uai-app-${_name}-${_uniqueSuffix}-deployment'
  params: {
    name: 'uai-app-${_name}-${_uniqueSuffix}'
    location: _location
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
  name: 'avm-registry-${_name}-${_uniqueSuffix}-deployment'
  params: {
    name: toLower(replace('registry-${_name}-${_uniqueSuffix}', '-', ''))
    acrAdminUserEnabled: false
    publicNetworkAccess: 'Enabled'
    location: _location
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

// Adjusting Connection String to use Managed Identity
var _storageConnString = 'ResourceId=${storageAccount.outputs.storageAccountId}'

var _containerEnvArray = [
  {
    name: 'AZURE_CLIENT_ID'
    value: appIdentity.outputs.clientId
  }
  {
    name: 'AZURE_OPENAI_API_VERSION'
    value: openAiApiVersion
  }
  {
    name: 'AZURE_OPENAI_API_VERSION_01'
    value: contains(reasoningModel.name, 'o1') || contains(reasoningModel.name, 'o3') ? openAiApiVersion : ''
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
    value: _docIntelligenceEndpoint
  }
  {
    name: 'AZURE_AI_SEARCH_ADMIN_KEY'
    value: searchService.outputs.searchServicePrimaryKey
  }
  {
    name: 'AZURE_STORAGE_CONNECTION_STRING'
    value: _storageConnString
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
    value: _docIntelligenceKey
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
  name: 'managedenv-${_name}-${_uniqueSuffix}-deployment'
  params: {
    // Required parameters
    logAnalyticsWorkspaceResourceId: monitoring.outputs.logAnalyticsWorkspaceResourceId
    name: toLower('managedEnv-${_name}-${_uniqueSuffix}')
    // Non-required parameters
    location: _location
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

var frontendContainerName = toLower('frontend-${_name}-${_uniqueSuffix}')
var backendContainerName = toLower('backend-${_name}-${_uniqueSuffix}')

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
    cpu: '2.0'
    memory: '4Gi'
  }
  env: union(_containerEnvArray, [
    {
      name: 'AZURE_OPENAI_ENDPOINT'
      value: _openAiEndpoint
    }
    {
      name: 'AZURE_OPENAI_KEY'
      value: _openAiKey
    }
  ])

}

// Due to limitations with the current Python SDK, the URL for the apim
//  endpoint does not meet the domain pattern requirements:
// Error in Vectorizer 'myOpenAI' : Invalid resourceUri. For Github endpoints, the uri
//  suffix must be inference.ai.azure.com. For Azure OpenAI endpoints, the uri suffix
//  must be one of: (openai.azure.com). Please provide a valid resourceUri for the Azure
//  OpenAI service.
// Therefore, providing a custom URL for the OpenAI endpoint for the indexer job
var _indexInitializationContainer = {
  name: '${backendContainerName}-job'
  image: frontendImage
  command: ['/bin/bash']
  resources: {
    cpu: '2.0'
    memory: '4Gi'
  }
  args: ['-c', 'python /app/src/pipeline/policyIndexer/indexerSetup.py --target \'/app\'']
  env: union(_containerEnvArray, [
    {
      name: 'AZURE_OPENAI_ENDPOINT'
      value: aiGateway.outputs.aiServices[0].endpoints.value.openAI
    }
    {
      name: 'AZURE_OPENAI_KEY'
      value: aiGateway.outputs.aiServices[0].key.value
    }
  ])
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
    location: _location
    tags: union(tags, { 'azd-service-name': 'frontend' })
  }
}

module indexInitializationJob 'br/public:avm/res/app/job:0.5.1' = {
  name: '${backendContainerName}-job'
  params: {
    // Required parameters
    containers: [
      _indexInitializationContainer
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
    location: _location
  }
}

// ----------------------------------------------------------------------------------------
// Enabling EasyAuth for the ContainerApps
// ----------------------------------------------------------------------------------------
var issuer = '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'
module easyAuthAppReg './modules/security/appregistration.bicep' = if (enableEasyAuth) {
  name: 'easyauth-reg'
  params: {
    clientAppName: '${priorAuthName}-${_uniqueSuffix}-easyauth-client-app'
    clientAppDisplayName: '${priorAuthName}-${_uniqueSuffix}-EasyAuth-app'
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

output AZURE_OPENAI_ENDPOINT string = _openAiEndpoint
output AZURE_OPENAI_API_VERSION string = openAiApiVersion
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = embeddingModel.name
output AZURE_OPENAI_CHAT_DEPLOYMENT_ID string = chatModel.name
output AZURE_OPENAI_CHAT_DEPLOYMENT_01 string = reasoningModel.name
output AZURE_OPENAI_API_VERSION_O1 string = reasoningModel.version
output AZURE_OPENAI_EMBEDDING_DIMENSIONS string = embeddingModelDimension
output AZURE_SEARCH_SERVICE_NAME string = searchService.outputs.searchServiceName
output AZURE_SEARCH_INDEX_NAME string = 'ai-policies-index'
output AZURE_AI_SEARCH_ADMIN_KEY string = searchService.outputs.searchServicePrimaryKey
output AZURE_AI_SEARCH_SERVICE_ENDPOINT string = searchService.outputs.searchServiceEndpoint
output AZURE_BLOB_CONTAINER_NAME string = storageBlobContainerName
output AZURE_STORAGE_ACCOUNT_NAME string = storageAccount.outputs.storageAccountName
output AZURE_STORAGE_CONNECTION_STRING string = _storageConnString
output AZURE_AI_SERVICES_KEY string = multiAccountAiServices.outputs.aiServicesPrimaryKey
output AZURE_COSMOS_DB_DATABASE_NAME string = 'priorauthsessions'

output AZURE_COSMOS_DB_COLLECTION_NAME string = 'temp'
output AZURE_COSMOS_CONNECTION_STRING string = cosmosDb.outputs.mongoConnectionString
output AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT string = _docIntelligenceEndpoint
output AZURE_DOCUMENT_INTELLIGENCE_KEY string = _docIntelligenceKey
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.applicationInsightsConnectionString
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.outputs.loginServer
output AZURE_CONTAINER_ENVIRONMENT_ID string = containerAppsEnvironment.outputs.resourceId
output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerAppsEnvironment.outputs.name
output AZURE_OPENAI_KEY string = _openAiKey
output AZURE_AI_FOUNDRY_CONNECTION_STRING string = aiFoundry.outputs.aiFoundryConnectionString
output CONTAINER_JOB_NAME string = indexInitializationJob.outputs.name

output FRONTEND_CONTAINER_URL string = frontendContainerApp.outputs.fqdn
output FRONTEND_CONTAINER_NAME string = frontendContainerApp.outputs.name
// output BACKEND_CONTAINER_URL string = backendContainerApp.outputs.fqdn
// output BACKEND_CONTAINER_NAME string = backendContainerApp.outputs.name
output APP_IDENTITY_CLIENT_ID string = appIdentity.outputs.clientId
output APP_IDENTITY_PRINCIPAL_ID string = appIdentity.outputs.principalId
