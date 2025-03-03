targetScope = 'subscription'

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
}

@description('API Version of the OpenAI API')
param openAiApiVersion string = '2024-08-01-preview'

@description('List of completion models to be deployed to the OpenAI account.')
param chatCompletionModels array = [
  {
    name: 'o1'
    version: '2024-12-17'
    skuName: 'Standard'
    capacity: 100
  }
]

@description('List of embedding models to be deployed to the OpenAI account.')
param embeddingModel object = {
    name: 'text-embedding-3-large'
    version: '1'
    skuName: 'Standard'
    capacity: 50
}

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
  'hidden-title': 'Prior Auth ${environmentName}'
  'azd-env-name': environmentName
})



// Organize resources in a resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'rg-${priorAuthName}-${location}-${environmentName}'
  location: location
  tags: azd_tags
}


module resources 'resources.bicep' = {
  scope: rg
  name: 'resources'
  params: {
    // Required Parameters
    priorAuthName: priorAuthName
    openAiApiVersion: openAiApiVersion
    chatCompletionModels: chatCompletionModels
    embeddingModel: embeddingModel
    embeddingModelDimension: embeddingModelDimension
    storageBlobContainerName: storageBlobContainerName
    // Optional Parameters
    tags: azd_tags
    frontendExists: frontendExists
    backendExists: backendExists
  }
}

// ----------------------------------------------------------------------------------------
// Setting the outputs at main.bicep (or whatever is defined in your azure.yaml's infra block) sets
//  the environment variables within azd post provisioning
// ----------------------------------------------------------------------------------------
@description('Name of the resource group')
output RESOURCE_GROUP_NAME string = rg.name

@description('Name of the container job')
output CONTAINER_JOB_NAME string = resources.outputs.CONTAINER_JOB_NAME

@description('Endpoint for Azure OpenAI')
output AZURE_OPENAI_ENDPOINT string = resources.outputs.AZURE_OPENAI_ENDPOINT

@description('API version for Azure OpenAI')
output AZURE_OPENAI_API_VERSION string = resources.outputs.AZURE_OPENAI_API_VERSION

@description('Deployment name for Azure OpenAI embedding')
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = resources.outputs.AZURE_OPENAI_EMBEDDING_DEPLOYMENT

@description('Deployment ID for Azure OpenAI chat')
output AZURE_OPENAI_CHAT_DEPLOYMENT_ID string = resources.outputs.AZURE_OPENAI_CHAT_DEPLOYMENT_ID

@description('Deployment name for Azure OpenAI chat model 01')
output AZURE_OPENAI_CHAT_DEPLOYMENT_01 string = resources.outputs.AZURE_OPENAI_CHAT_DEPLOYMENT_01

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
