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

// Given O1's availabilities are limited to eastus2 and swedencentral, we will configure the backend's reasoning pool to be on only 2 of 3 ai services
var backend_regions = ['eastus2', 'swedencentral']

var allowedO1Regions = [
  'eastus2'
  'swedencentral'
]

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
  'Developer'
  'BasicV2'
  'StandardV2'
  'Premium'
  // 'PremiumV2' // Currently in Preview
])
param sku string = 'BasicV2'
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
    value: localClientId ?? appClientId
    secret: false
  }
  {
    displayName: 'AutoAuthApp'
    name: 'AutoAuthApp'
    value: appClientId
    secret: false
  }
])

// ===========================================================
// Section: API Management (APIM)
// ===========================================================
module apim 'br/public:avm/res/api-management/service:0.8.0' = {
  name: name
  params: {
    // Required parameters
    name: 'apim-${name}-${resourceSuffix}'
    publisherEmail: apimPublisherEmail
    publisherName: apimPublisherName
    location: location
    sku: sku
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



//===========================================================
// OpenAI Backend + Backend Pool (if multiple deployments)
//===========================================================
// Deploy individual OpenAI backend instances
module openAIBackend './modules/apim/backend.bicep' = if (length(openAIInstances) > 0) {
  name: 'module-backend-openai-${name}-${resourceSuffix}'
  params: {
    apimName: _apim.name
    backendInstances: openAIInstances
    backendPoolName: 'openai-backend-pool'
    // Add additional backend configurations if needed
  }
}

module docIntelBackend './modules/apim/backend.bicep' = if (length(docIntelInstances) > 0) {
  name: 'module-backend-docintel-${name}-${resourceSuffix}'
  params: {
    apimName: _apim.name
    backendInstances: docIntelInstances
    backendPoolName: 'docintel-backend-pool'
  }
}

//===========================================================
// API Configuration + Named Values
//===========================================================
module openAIAPI './modules/apim/api.bicep' = if (length(openAIInstances) > 0) {
  name: 'module-api-openai-${name}-${resourceSuffix}'
  params: {
    apimName: _apim.name                // expected path, e.g. 'openai'
    // API resource properties
    name: 'api-openai-${name}-${resourceSuffix}'
    apiPath: 'openai'
    apiDescription: 'Azure OpenAI API'            // e.g. 'Azure OpenAI API inferencing API'
    apiDisplayName: 'Auto Auth OpenAI API'               // e.g. 'AutoAuth OpenAI API'
    apiSpecURL: openAIAPISpecURL

    // Policy properties
    policyContent: loadTextContent('./modules/apim/policies/openai/inbound.xml')

    // Subscription properties
    apiSubscriptionName: 'openai-subscription'
    apiSubscriptionDescription: 'AutoAuth OpenAI Subscription'
  }

  dependsOn: [
    openAIBackend
  ]
}


module docIntelAPI './modules/apim/api.bicep' = if (length(docIntelInstances) > 0) {
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
