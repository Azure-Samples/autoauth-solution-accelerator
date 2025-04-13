/*
  Inputs:
  - Regional deployments of Azure AI Services instances (both OpenAI and DocIntel)
    - Outline which deployments should go where (i.e eus has chat/reasoning, vs eus2 which has chat/reasoning/embedding)
  -  Is it better to just customize this current module to have everything?
    - i.e just take inputs for which backend regions, and then deploy everything here?


    - main.bicep (takes in flag, optional parameter set with defaults?)
    - resources.bicep (invokes this module)
      - Passes in the following inputs:
        - chat model
        - reasoning model
        - embedding model
        - backend config
*/
import { ModelConfig, BackendConfigItem } from './modules/ai/types.bicep'


param name string
param location string = resourceGroup().location
param env string?
param enableSystemAssignedIdentity bool = true
param userAssignedResourceIds array?

@description('Optional. The diagnostic settings of the service.')
param diagnosticSettings array = [
  // {
  //   eventHubAuthorizationRuleResourceId: '<eventHubAuthorizationRuleResourceId>'
  //   eventHubName: '<eventHubName>'
  //   storageAccountResourceId: '<storageAccountResourceId>'
  //   workspaceResourceId: '<workspaceResourceId>'
  // }
]

// var o1_enabled = contains(reasoningModel.name, 'o1') || contains(reasoningModel.name, 'o3')

// // Given O1's availabilities are limited to eastus2 and swedencentral, we will configure the backend's reasoning pool to be on only 2 of 3 ai services
// var o1SupportedRegions = o1_enabled ? [
//   'westus2'
//   'swedencentral'
// ] : []

// var allowedO1Regions = [
//   'eastus2'
//   'swedencentral'
// ]

// Authentication / Access settings
@description('Optionally provide a client ID for the local test account. If not provided, the client ID from the AutoAuth App will be used.')
param localClientId string = ''

// Authentication: AutoAuth App Client ID (required)
@description('Client ID for the AutoAuth App. Required to authorize the client to use the OpenAI API.')
param appClientId string

// APIM Parameters
param apimPublisherEmail string = 'noreply@microsoft.com'
param apimPublisherName string = 'Microsoft'
param openAIAPISpecURL string = 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/specification/cognitiveservices/data-plane/AzureOpenAI/inference/stable/2024-02-01/inference.json'
param docIntelAPISpecURL string = 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/refs/heads/main/specification/cognitiveservices/data-plane/FormRecognizer/stable/2023-07-31/FormRecognizer.json'

@allowed([
  'S0'
])
param aiServicesSku string = 'S0'

@allowed([
  'BasicV2'
  'StandardV2'
])
param apimSku string = 'BasicV2'

param namedValues array = [
  // {
  //   name: 'exampleNamedValue1'
  //   value: 'Value1'
  //   secret: false
  // }
  // {
  //   name: 'exampleNamedValue2'
  //   value: 'Value2'
  //   secret: true
  // }
]

// OpenAI Backend/Backend Pool Parameters
param openAIInstances array = []

param docIntelInstances array = []


import { lockType } from 'br/public:avm/utl/types/avm-common-types:0.4.1'
param lock lockType = {
  name: null
  kind: env == 'prod' ? 'CanNotDelete' : 'None'
}

param tags object = {}

var resourceSuffix = uniqueString(subscription().id, resourceGroup().id)
var _namedValues = concat(namedValues, [
  {
    displayName: 'LocalAccountApp'
    name: 'LocalAccountApp'
    value: localClientId == '' ? appClientId : localClientId
    secret: false
  }
  {
    displayName: 'AutoAuthApp'
    name: 'AutoAuthApp'
    value: appClientId
    secret: false
  }
])

// ============================================================
// Section: AI Services for each backendConfig object
// ============================================================

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

param backendConfig BackendConfigItem[] = [
  {
    name: 'eus2'
    priority: 1
    location: location ?? 'eastus2'
    chat: {
      sku: chatModel.sku
      capacity: chatModel.capacity
      name: chatModel.name
      version: chatModel.version
    }
    reasoning: {
      sku: reasoningModel.sku
      capacity: reasoningModel.capacity
      name: reasoningModel.name
      version: reasoningModel.version
    }
    embedding: {
      sku: embeddingModel.sku
      capacity: embeddingModel.capacity
      name: embeddingModel.name
      version: embeddingModel.version
    }
  }
  {
    name: 'sc'
    priority: 2
    location: 'swedencentral'
    chat: {
      sku: chatModel.sku
      capacity: chatModel.capacity
      name: chatModel.name
      version: chatModel.version
    }
    reasoning: {
      sku: reasoningModel.sku
      capacity: reasoningModel.capacity
      name: reasoningModel.name
      version: reasoningModel.version
    }
    embedding: {
      sku: embeddingModel.sku
      capacity: embeddingModel.capacity
      name: embeddingModel.name
      version: embeddingModel.version
    }
  }
  // {
  //   name: 'wus2'
  //   priority: 3
  //   location: 'westus2'
  //   chat: {
  //     sku: chatModel.sku
  //     capacity: chatModel.capacity
  //     name: chatModel.name
  //     version: chatModel.version
  //   }
  //   reasoning: {
  //     sku: reasoningModel.sku
  //     capacity: reasoningModel.capacity
  //     name: reasoningModel.name
  //     version: reasoningModel.version
  //   }
  // }
]

// Expected outputs from AI Services:
// - IF exists, endpoints for:
//  - chatModel, embeddingModel, reasoningModel
//  - documentIntelligence
@batchSize(1)
module aiServices './modules/ai/aiservices.bicep' = [for (backend, i) in backendConfig: {
  name: 'module-ai-services-${backend.name}${name}${resourceSuffix}'
  params: {
    name: '${backend.name}${name}${resourceSuffix}'
    location: backend.location
    sku: aiServicesSku
    tags: tags
    openAIUserClientIds: [
      appClientId
      localClientId
    ]
    models: concat(
      contains(backend, 'chat') ? [backend.?chat] : [],
      contains(backend, 'reasoning') ? [backend.?reasoning] : [],
      contains(backend, 'embedding') ? [backend.?embedding] : []
    )
  }
}]


// Loop through client IDs and assign the OpenAI User role to each client using the managed identity scope.
resource azureAIDeveloperRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(resourceGroup().name, appClientId, 'Azure AI Developer')
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '64702f94-c441-49e6-a78b-ef80e0188fee')
    principalId: appClientId
  }
}


// ===========================================================
// Section: API Management (APIM)
// ===========================================================
module apim 'br/public:avm/res/api-management/service:0.9.1' = {
  name: 'apim-${name}-${resourceSuffix}'
  params: {
    // Required parameters
    name: 'apim-${name}-${resourceSuffix}'
    publisherEmail: apimPublisherEmail
    publisherName: apimPublisherName
    location: location
    sku: apimSku
    namedValues: _namedValues
    lock: lock
    managedIdentities: {
      systemAssigned: enableSystemAssignedIdentity
      userAssignedResourceIds: userAssignedResourceIds
    }

    diagnosticSettings: diagnosticSettings

    tags: tags
  }
}

resource _apim 'Microsoft.ApiManagement/service@2022-08-01' existing = {
  name: apim.name
}

// Add role assignment for APIM system-assigned identity to access each AI service
resource apimSystemMIDRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableSystemAssignedIdentity) {
  name: guid(resourceGroup().id, _apim.id, 'Azure-AI-Developer')
  scope: resourceGroup()

  properties: {
    principalId: _apim.identity.principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '64702f94-c441-49e6-a78b-ef80e0188fee') // Azure AI Developer role
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    aiServices
  ]
}

resource uaiAIServiceRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for (id, i) in (userAssignedResourceIds ?? []): {
  name: guid(resourceGroup().id, id, 'Azure-AI-Developer')
  scope: resourceGroup()

  properties: {
    principalId: id
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '64702f94-c441-49e6-a78b-ef80e0188fee') // Azure AI Developer role
    principalType: 'ServicePrincipal'
  }
  dependsOn: [
    aiServices
  ]
}]

//===========================================================
// OpenAI Backend + Backend Pool (if multiple deployments)
//===========================================================
// Deploy individual OpenAI backend instances

module openAIBackendPool './modules/apim/backend.bicep' = {
  name: 'module-backend-openai-${name}-${resourceSuffix}'
  params: {
    apimName: _apim.name
    backendInstances: [ for (backend, i) in backendConfig: {
      name: 'oai-${backend.name}'
      priority: backend.?priority ?? 1
      url: aiServices[i].outputs.openAIEndpoint
      description: '${aiServices[i].name} openai endpoint with priority ${backend.?priority ?? 1} based out of ${aiServices[i].outputs.location}'
    }]
    backendPoolName: 'openai-backend-pool'
    // Add additional backend configurations if needed
  }
}

module docIntelBackend './modules/apim/backend.bicep' = {
  name: 'module-backend-docintel-${name}-${resourceSuffix}'
  params: {
    apimName: _apim.name
    backendInstances: [ for (backend, i) in backendConfig: {
      name: 'docintel-${backend.name}'
      priority: backend.?priority ?? 1
      url: aiServices[i].outputs.docIntelEndpoint
      description: '${aiServices[i].name} Document Intelligence Endpoint with priority ${backend.?priority ?? 1} based out of ${aiServices[i].outputs.location}'
    }]
    backendPoolName: 'docintel-backend-pool'
  }
}


module openAIAPI './modules/apim/api.bicep' = {
  name: 'module-api-openai-${name}-${resourceSuffix}'
  params: {
    apimName: _apim.name
    // API resource properties
    name: 'api-openai-${name}-${resourceSuffix}'
    apiPath: 'openai'
    apiDescription: 'Azure OpenaI API'
    apiDisplayName: 'Auto Auth OpenAI API'
    apiSpecURL: openAIAPISpecURL

    // Policy properties
    policyContent: loadTextContent('./modules/apim/policies/openAI/inbound.xml')

    // Subscription properties
    apiSubscriptionName: 'openai-subscription'
    apiSubscriptionDescription: 'AutoAuth OpenAI Subscription'
  }

  dependsOn: [
    docIntelBackend
  ]
}

module docIntelAPI './modules/apim/api.bicep' = {
  name: 'module-api-docintel-${name}-${resourceSuffix}'
  params: {
    apimName: _apim.name
    // API resource properties
    name: 'api-docintel-${name}-${resourceSuffix}'
    apiPath: 'docintel'
    apiDescription: 'Azure Document Intelligence API'
    apiDisplayName: 'Auto Auth Document Intelligence API'
    apiSpecURL: docIntelAPISpecURL

    // Policy properties
    policyContent: loadTextContent('./modules/apim/policies/docIntel/inbound.xml')

    // Subscription properties
    apiSubscriptionName: 'docintel-subscription'
    apiSubscriptionDescription: 'AutoAuth DocIntel Subscription'
  }

  dependsOn: [
    docIntelBackend
  ]
}

//===========================================================
// Output
//===========================================================
@description('API Management Module Output Object')
output name string = _apim.name

output id string = _apim.id

output location string = _apim.location

output sku string = _apim.sku.name

output publisherEmail string = _apim.properties.publisherEmail

output publisherName string = _apim.properties.publisherName

output namedValues array = _namedValues

@description('Subscription resource IDs for the deployed APIs (or null if not deployed)')
output subscriptions object = {
  openAI: length(openAIInstances) > 0 ? openAIAPI.outputs.apiSubscriptionId : null
  docIntelligence: length(docIntelInstances) > 0 ? docIntelAPI.outputs.apiSubscriptionId : null
}

@description('API endpoint URLs for the deployed APIs (or null if not deployed)')
output endpoints object = {
  openAI: length(openAIInstances) > 0 ? '${_apim.properties.gatewayUrl}/${openAIAPI.outputs.apiPath}' : null
  docIntelligence: length(docIntelInstances) > 0 ? '${_apim.properties.gatewayUrl}/${docIntelAPI.outputs.apiPath}' : null
}
// output subscriptionKeys object = {
//   openAI: 'openAIAPI.outputs.apiSubscriptionKey'
//   docIntel: 'docIntelAPI.outputs.apiSubscriptionKey'
// }

// output endpoints object = {
//   openAI: 'openAIAPI.outputs.serviceUrl'
//   docIntel: 'docIntelAPI.outputs.serviceUrl'
// }

output identity object = _apim.identity
