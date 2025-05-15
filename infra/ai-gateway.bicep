/*
  This module deploys AI Gateway infrastructure, including:
  - Azure AI Services (OpenAI, Document Intelligence)
  - API Management (APIM) for managing APIs
  - Role assignments for APIM to access AI services
*/

import { ModelConfig, BackendConfigItem } from './modules/ai/types.bicep'

// Parameters
@description('The name of the deployment or resource.')
param name string

@description('The location where the resources will be deployed. Defaults to the resource group location.')
param location string = resourceGroup().location

@description('The environment for the deployment (e.g., dev, test, prod).')
param env string?

@description('Flag to enable or disable the use of a system-assigned managed identity.')
param enableSystemAssignedIdentity bool = true

@description('An array of user-assigned managed identity resource IDs to be used.')
param userAssignedResourceIds array?

@description('An array of diagnostic settings to configure for the resources.')
param diagnosticSettings array = []

@description('The email address of the API Management publisher.')
param apimPublisherEmail string = 'noreply@microsoft.com'

@description('The name of the API Management publisher.')
param apimPublisherName string = 'Microsoft'

@description('Flag to enable API Management for AI Services')
param enableAPIManagement bool = false

param openAIAPISpecURL string = 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/specification/cognitiveservices/data-plane/AzureOpenAI/inference/stable/2024-02-01/inference.json'
// param docIntelAPISpecURL string = 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/refs/heads/main/specification/cognitiveservices/data-plane/FormRecognizer/stable/2023-07-31/FormRecognizer.json'

@allowed(['S0'])
param aiServicesSku string = 'S0'

@allowed(['BasicV2', 'StandardV2'])
param apimSku string = 'BasicV2'

param namedValues array = []

import { lockType } from 'br/public:avm/utl/types/avm-common-types:0.4.1'
param lock lockType = {
  name: null
  kind: env == 'prod' ? 'CanNotDelete' : 'None'
}

param tags object = {}

var resourceSuffix = uniqueString(subscription().id, resourceGroup().id)

// Default Model Configurations
@description('Chat model configuration for deployment')
param chatModel ModelConfig = {
  sku: 'GlobalStandard'
  capacity: 10
  name: 'gpt-4o'
  version: '2024-08-06'
}

@description('Reasoning model configuration for deployment')
param reasoningModel ModelConfig = {
  sku: 'GlobalStandard'
  capacity: 10
  name: 'o1'
  version: '2025-01-01-preview'
}

@description('Embedding model configuration for deployment')
param embeddingModel ModelConfig = {
  sku: 'Standard'
  capacity: 10
  name: 'text-embedding-3-large'
  version: '1'
}

// Backend Configuration
param backendConfig BackendConfigItem[] = [
  {
    name: 'eus2'
    priority: 1
    location: location ?? 'eastus2'
    chat: chatModel
    reasoning: reasoningModel
    embedding: embeddingModel
  }
]

var _backendConfig = enableAPIManagement ? backendConfig : [
  {
    name: 'aiServices${location}'
    priority: 1
    location: location
    chat: chatModel
    reasoning: reasoningModel
    embedding: embeddingModel
  }
]

// AI Services Deployment
@batchSize(1)
module aiServices './modules/ai/aiservices.bicep' = [for (backend, i) in _backendConfig: {
  name: 'aigw-ai-services-${i}-${backend.location}'
  params: {
    name: '${backend.name}${name}${resourceSuffix}'
    location: backend.location
    sku: aiServicesSku
    tags: tags
    models: concat(
      contains(backend, 'chat') ? [backend.?chat] : [],
      contains(backend, 'reasoning') ? [backend.?reasoning] : [],
      contains(backend, 'embedding') ? [backend.?embedding] : []
    )
  }
}]

// API Management Deployment
module apim 'br/public:avm/res/api-management/service:0.9.1' = if (enableAPIManagement) {
  name: 'apim-${name}-${resourceSuffix}'
  params: {
    name: 'apim-${name}-${resourceSuffix}'
    publisherEmail: apimPublisherEmail
    publisherName: apimPublisherName
    location: location
    sku: apimSku
    namedValues: namedValues
    lock: lock
    managedIdentities: {
      systemAssigned: enableSystemAssignedIdentity
      userAssignedResourceIds: userAssignedResourceIds
    }
    diagnosticSettings: diagnosticSettings
    tags: tags
  }
}

resource _apim 'Microsoft.ApiManagement/service@2022-08-01' existing = if (enableAPIManagement) {
  name: apim.name
}

// Role Assignments for APIM
resource apimSystemMIDRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableAPIManagement && enableSystemAssignedIdentity) {
  name: guid(resourceGroup().id, _apim.id, 'Azure-AI-Developer')
  scope: resourceGroup()
  properties: {
    principalId: _apim.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '64702f94-c441-49e6-a78b-ef80e0188fee')
    principalType: 'ServicePrincipal'
  }
  dependsOn: [aiServices]
}


// Backend Pools
module openAIBackendPool './modules/apim/backend.bicep' = if (enableAPIManagement) {
  name: 'module-backend-openai-${resourceSuffix}'
  params: {
    apimName: _apim.name
    backendInstances: [for (backend, i) in backendConfig: {
      name: 'oai-${backend.name}'
      priority: backend.?priority ?? 1
      url: aiServices[i].outputs.endpoints.openAI
      description: '${aiServices[i].?name} OpenAI endpoint with priority ${backend.?priority ?? 1} in ${aiServices[i].outputs.?location}'
    }]
    backendPoolName: 'openai-backend-pool'
  }
}

// APIs
module openAiApi './modules/apim/api.bicep' = if (enableAPIManagement) {
  name: 'api-openai-${resourceSuffix}'
  params: {
    apimName: _apim.name
    name: 'api-openai-${name}-${resourceSuffix}'
    apiPath: 'openai'
    apiDescription: 'Azure OpenAI API'
    apiDisplayName: 'Auto Auth OpenAI API'
    apiSpecURL: openAIAPISpecURL
    policyContent: loadTextContent('./modules/apim/policies/openAI/inbound.xml')
    apiSubscriptionName: 'openai-subscription'
    apiSubscriptionDescription: 'AutoAuth OpenAI Subscription'
  }
}

// Outputs
output apim object = enableAPIManagement ? {
  name: _apim.name
  id: _apim.id
  location: _apim.location
  sku: _apim.sku.name
  publisherEmail: _apim.properties.publisherEmail
  publisherName: _apim.properties.publisherName
} : {}


resource uaiAIServiceRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (id, i) in (userAssignedResourceIds ?? []): {
  name: guid(resourceGroup().id, id, 'Azure-AI-Developer')
  scope: resourceGroup()
  properties: {
    principalId: id
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '64702f94-c441-49e6-a78b-ef80e0188fee')
    principalType: 'ServicePrincipal'
  }
  dependsOn: [aiServices]
}]
@description('API endpoint URLs for the deployed APIs (or null if not deployed)')
output endpoints object = {
  openAI: enableAPIManagement ? '${_apim.properties.gatewayUrl}/${openAiApi.outputs.apiPath}' : aiServices[0].outputs.endpoints.openAI
}

@description('Subscription keys for the deployed APIs (or null if not deployed)')
output subscriptionKeys object = {
  openAI: enableAPIManagement ? openAiApi.outputs.apiSubscriptionKey : aiServices[0].outputs.key
}

output identity object = _apim.identity

@description('Resource IDs of the deployed AI Services')
output aiServicesIds array = [for (item, i) in backendConfig: aiServices[i].outputs.id]

@description('AI Services module outputs')
output aiServices array = [for (item, i) in backendConfig: aiServices[i].outputs]

@description('Resource names of the deployed AI Services')
output aiServicesNames array = [for (item, i) in backendConfig: aiServices[i].outputs.name]
