targetScope = 'subscription'

@description('Flag to indicate if EasyAuth should be enabled for the Container Apps (Defaults to true)')
param enableEasyAuth bool = false

@minLength(1)
@maxLength(64)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string

@minLength(1)
@description('Primary location for all resources. Not all regions are supported due to OpenAI limitations')
@allowed([
  'australiaeast'
  'canadaeast'
  'eastus'
  'eastus2'
  'francecentral'
  'japaneast'
  'norwayeast'
  'polandcentral'
  'southindia'
  'swedencentral'
  'switzerlandnorth'
  'uksouth'
  'westus3'
])
param location string

@description('Flag to indicate if Frontend app image exists. This is managed by AZD')
param frontendExists bool = false

@description('Flag to indicate if Backend app image exists. This is managed by AZD')
param backendExists bool = false

@minLength(2)
@maxLength(12)
@description('Name for the PriorAuth resource and used to derive the name of dependent resources.')
param priorAuthName string = 'priorAuth'

@description('Tags to be applied to all resources')
param tags object = {
  environment: environmentName
  location: location
  commit: GIT_HASH
}

@description('API Version of the OpenAI API')
param openAiApiVersion string = '2025-01-01-preview'

@description('Reasoning model object to be deployed to the OpenAI account. (i.e o1, o1-preview, o3-mini)')
param reasoningModel object = {
  name: 'o1'
  version: '2025-01-01-preview'
  skuName: 'GlobalStandard'
  capacity: 100
}

@description('Chat model object to be deployed to the OpenAI account. (i.e gpt-4o, gpt-4o-turbo, gpt-4o-turbo-16k, gpt-4o-turbo-32k)')
param chatModel object = {
  name: 'gpt-4o'
  version: '2024-08-06'
  skuName: 'Standard'
  capacity: 100
}

@description('Embedding model to be deployed to the OpenAI account.')
param embeddingModel object = {
    name: 'text-embedding-3-large'
    version: '1'
    skuName: 'Standard'
    capacity: 50
}

@description('Unique hash of the git commit that is being deployed. This is used to tag resources and support llm evaluation automation.')
param GIT_HASH string = 'azd-deploy-1741105197' // This is the git hash of the commit that is being deployed. It is used to tag the image in ACR and also used to tag the container job in ACI. This is set by azd during deployment.

@description('Embedding model size for the OpenAI Embedding deployment')
param embeddingModelDimension string = '3072' // for embeddings-3-large, 3072 is expected

@description('Storage Blob Container name to land the files for Prior Auth')
param storageBlobContainerName string = 'default'

// Tags that should be applied to all resources.
//
// Note that 'azd-service-name' tags should be applied separately to service host resources.
// Example usage:
//   tags: union(tags, { 'azd-service-name': <service name in azure.yaml> })
var azd_tags = union(tags,{
  'hidden-title': 'Auto Auth ${environmentName}'
  'azd-env-name': environmentName
})


// ----------------------------------------------------------------------------------------
// Creating the resource group for the PriorAuth solution
// ----------------------------------------------------------------------------------------
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'rg-${priorAuthName}-${location}-${environmentName}'
  location: location
  tags: azd_tags
}

// ----------------------------------------------------------------------------------------
// Deploying the main components of the PriorAuth solution
// ----------------------------------------------------------------------------------------
module resources 'resources.bicep' = {
  scope: rg
  name: 'autoauth-resources'
  params: {
    // Required Parameters
    priorAuthName: priorAuthName
    openaiApiVersion: openAiApiVersion
    chatModel: chatModel
    reasoningModel: reasoningModel
    embeddingModel: embeddingModel
    embeddingModelDimension: embeddingModelDimension
    storageBlobContainerName: storageBlobContainerName
    // Optional Parameters
    enableEasyAuth: enableEasyAuth
    tags: azd_tags
    gitHash: GIT_HASH
    frontendExists: frontendExists
    backendExists: backendExists
  }
}



// ----------------------------------------------------------------------------------------
// Setting the outputs at main.bicep (or whatever is defined in your azure.yaml's infra block) sets
//  the environment variables within azd post provisioning
// ----------------------------------------------------------------------------------------
@description('Name of the resource group')
output AZURE_RESOURCE_GROUP string = rg.name

@description('Name of the container job')
output CONTAINER_JOB_NAME string = resources.outputs.CONTAINER_JOB_NAME

@description('Endpoint for Azure OpenAI')
output AZURE_OPENAI_ENDPOINT string = resources.outputs.AZURE_OPENAI_ENDPOINT

@description('API version for Azure OpenAI')
output AZURE_OPENAI_API_VERSION string = openAiApiVersion

@description('API version for Azure OpenAI O1')
output AZURE_OPENAI_API_VERSION_O1 string = openAiApiVersion

@description('Deployment name for Azure OpenAI embedding')
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = resources.outputs.AZURE_OPENAI_EMBEDDING_DEPLOYMENT

@description('Deployment ID for Azure OpenAI chat')
output AZURE_OPENAI_CHAT_DEPLOYMENT_ID string = resources.outputs.AZURE_OPENAI_CHAT_DEPLOYMENT_ID

@description('Deployment name for Azure OpenAI chat model 01')
output AZURE_OPENAI_CHAT_DEPLOYMENT_01 string = resources.outputs.AZURE_OPENAI_CHAT_DEPLOYMENT_01

@description('Deployment openai version for chat model 01')
output AZURE_OPENAI_API_VERSION_01 string = resources.outputs.AZURE_OPENAI_API_VERSION_O1

@description('Embedding dimensions for Azure OpenAI')
output AZURE_OPENAI_EMBEDDING_DIMENSIONS string = resources.outputs.AZURE_OPENAI_EMBEDDING_DIMENSIONS

@description('Name of the Azure Search service')
output AZURE_SEARCH_SERVICE_NAME string = resources.outputs.AZURE_SEARCH_SERVICE_NAME

@description('Name of the Azure Search index')
output AZURE_SEARCH_INDEX_NAME string = resources.outputs.AZURE_SEARCH_INDEX_NAME

@description('Admin key for Azure AI Search')
output AZURE_AI_SEARCH_ADMIN_KEY string = resources.outputs.AZURE_AI_SEARCH_ADMIN_KEY

@description('Name of the Azure Blob container')
output AZURE_BLOB_CONTAINER_NAME string = resources.outputs.AZURE_BLOB_CONTAINER_NAME

@description('Name of the Azure Storage account')
output AZURE_STORAGE_ACCOUNT_NAME string = resources.outputs.AZURE_STORAGE_ACCOUNT_NAME

@description('Key for the Azure Storage account')
output AZURE_STORAGE_ACCOUNT_KEY string = resources.outputs.AZURE_STORAGE_ACCOUNT_KEY

@description('Connection string for the Azure Storage account')
output AZURE_STORAGE_CONNECTION_STRING string = resources.outputs.AZURE_STORAGE_CONNECTION_STRING

@description('Key for Azure AI services')
output AZURE_AI_SERVICES_KEY string = resources.outputs.AZURE_AI_SERVICES_KEY

@description('Name of the Azure Cosmos DB database')
output AZURE_COSMOS_DB_DATABASE_NAME string = resources.outputs.AZURE_COSMOS_DB_DATABASE_NAME

@description('Name of the Azure Cosmos DB collection')
output AZURE_COSMOS_DB_COLLECTION_NAME string = resources.outputs.AZURE_COSMOS_DB_COLLECTION_NAME

@description('Connection string for Azure Cosmos DB')
output AZURE_COSMOS_CONNECTION_STRING string = resources.outputs.AZURE_COSMOS_CONNECTION_STRING

@description('Endpoint for Azure Document Intelligence')
output AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT string = resources.outputs.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT

@description('Key for Azure Document Intelligence')
output AZURE_DOCUMENT_INTELLIGENCE_KEY string = resources.outputs.AZURE_DOCUMENT_INTELLIGENCE_KEY

@description('Connection string for Application Insights')
output APPLICATIONINSIGHTS_CONNECTION_STRING string = resources.outputs.APPLICATIONINSIGHTS_CONNECTION_STRING

@description('Endpoint for Azure Container Registry')
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.AZURE_CONTAINER_REGISTRY_ENDPOINT

@description('ID for Azure Container Environment')
output AZURE_CONTAINER_ENVIRONMENT_ID string = resources.outputs.AZURE_CONTAINER_ENVIRONMENT_ID

@description('Key for Azure OpenAI')
output AZURE_OPENAI_KEY string = resources.outputs.AZURE_OPENAI_KEY

@description('Service endpoint for Azure AI Search')
output AZURE_AI_SEARCH_SERVICE_ENDPOINT string = resources.outputs.AZURE_AI_SEARCH_SERVICE_ENDPOINT

@description('AI Foundry connection string to connect to AI Foundry')
output AZURE_AI_FOUNDRY_CONNECTION_STRING string = resources.outputs.AZURE_AI_FOUNDRY_CONNECTION_STRING

// @description('Evaluation Job Name')
// output CONTAINER_EVALUATION_NAME string = resources.outputs.CONTAINER_EVALUATION_NAME
