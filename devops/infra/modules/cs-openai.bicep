@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('Name of the AI service')
param aiServiceName string

@allowed([
  'S0'
])
@description('AI service SKU')
param aiServiceSkuName string = 'S0'

@description('List of chat completion models to be deployed to the OpenAI account.')
param chatCompletionModels array = [
  {
    name: 'gpt-4o'
    version: '2024-08-06'
    skuName: 'GlobalStandard'
    capacity: 25
  }
]

@description('List of embedding models to be deployed to the OpenAI account.')
param embeddingModel object = {
    name: 'text-embedding-ada-002'
    version: '2'
    skuName: 'Standard'
    capacity: 16
}

var combinedModels = concat(chatCompletionModels, [embeddingModel])

var aiServiceNameCleaned = replace(aiServiceName, '-', '')

resource openAiService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: aiServiceNameCleaned
  location: location
  sku: {
    name: aiServiceSkuName
  }
  kind: 'OpenAI'
  properties: {
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
    apiProperties: {
      statisticsEnabled: false
    }
    customSubDomainName: aiServiceNameCleaned
  }
  identity: {
    type: 'SystemAssigned'
  }
  tags: tags
}

@batchSize(1)
resource modelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2024-06-01-preview' = [for (model, i) in combinedModels: {
  parent: openAiService
  name: '${model.name}'
  sku: {
    name: model.skuName
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

var openAiKeys = openAiService.listKeys()

output aiServicesId string = openAiService.id
output aiServicesEndpoint string = openAiService.properties.endpoint
output aiServicesName string = openAiService.name
output aiServicesPrincipalId string = openAiService.identity.principalId
output aiServicesKey string = openAiKeys.key1
