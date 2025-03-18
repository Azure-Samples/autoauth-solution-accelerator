//////////////////////////////////////////////
// AI Services Module
//
// This module creates an AI service resource using the CognitiveServices API,
// assigns a managed identity, and grants the OpenAI User role to specified clients.
//
// Supported AI Services:
//   • Azure Cognitive Services for OpenAI
//   • Azure Cognitive Services for Document Intelligence
//
// Parameters:
//   • location: The Azure region where the resource will be deployed.
//   • tags: An object representing the tags to apply to all resources.
//   • openAIUserClientIds: An array of client IDs assigned the OpenAI User role.
//   • oaiModels: An array of OpenAI models to be deployed to the AI service.
//
// Outputs:
//   • aiServicesId: The resource ID of the created AI service.
//   • aiServicesName: The name of the AI service.
//   • aiServicesPrincipalId: The managed identity principal ID for the AI service.
//   • endpoints: An object with various endpoints for accessing the created service.
//////////////////////////////////////////////

@description('Azure region of the deployment.')
param location string

@description('Tags to add to the resources.')
param tags object

@description('Name of the AI service. Note: Only alphanumeric characters and no dashes used to ensure DNS compatibility.')
param name string

@allowed([
  'S0'
])
@description('AI service SKU. Only S0 is currently allowed.')
param sku string = 'S0'

@description('List of client IDs to grant OpenAI User role.')
param openAIUserClientIds array = []

param openAIModels array = []



// Clean the AI service name by removing dashes to ensure valid DNS names
var aiServicesHostname = '${name}.cognitiveservices.azure.com'

// Define the AI service resource with managed identity
resource aiServices 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: name
  location: location
  sku: {
    name: sku
  }
  kind: 'AIServices'
  properties: {
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    apiProperties: {
      statisticsEnabled: false
    }
    customSubDomainName: aiServicesHostname
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
}

@batchSize(1)
resource modelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2024-06-01-preview' = [for (model, i) in openAIModels: {
  parent: aiServices
  name: '${model.name}'
  sku: {
    name: model.sku
    capacity: model.capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: model.name
      version: model.version
    }
    currentCapacity: model.capacity
  }
}]

// Loop through client IDs and assign the OpenAI User role to each client using the managed identity scope.
resource openAIUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = [for clientId in openAIUserClientIds: {
  name: guid(aiServices.id, clientId, 'CognitiveServicesOpenAIUser')
  scope: aiServices
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '146c0133-10bd-4905-8e44-40779abb5e79')
    principalId: clientId
  }
}]

// Outputs for integration and further automation
output id string = aiServices.id
output name string = aiServices.name
output principalId string = aiServices.identity.principalId
output key string = aiServices.listKeys().key1

output openAIEndpoint string = aiServices.properties.endpoints.openAI
output docIntelEndpoint string = aiServices.properties.endpoints.documentIntelligence
