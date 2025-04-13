using './ai-gateway.bicep'

// Required parameters
param name = 'ai-gateway-test'
param appClientId = '338763bc-c5e4-4157-8f03-a86a0dff5711'
param localClientId = '04b07795-8ddb-461a-bbee-02f9e1bf7b46'
// Optional parameters (commented out, will use defaults)
param apimSku = 'StandardV2'
// AI model configurations
param chatModel = {
  name: 'gpt-4o'
  version: '2024-08-06'
  sku: 'GlobalStandard'
  capacity: 10
}

param reasoningModel = {
  name: 'o1'
  version: '2024-12-17'
  sku: 'GlobalStandard'
  capacity: 10
}

param embeddingModel = {
  name: 'text-embedding-3-large'
  version: '1'
  sku: 'Standard'
  capacity: 10
}

/*
param location = 'eastus2'
param env = 'dev'
param enableSystemAssignedIdentity = true
param userAssignedResourceIds = []
param diagnosticSettings = []
param localClientId = ''
param apimPublisherEmail = 'admin@contoso.com'
param apimPublisherName = 'Contoso Ltd'
param openAIAPISpecURL = 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/specification/cognitiveservices/data-plane/AzureOpenAI/inference/stable/2024-02-01/inference.json'
param docIntelAPISpecURL = 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/refs/heads/main/specification/cognitiveservices/data-plane/FormRecognizer/stable/2023-07-31/FormRecognizer.json'
param aiServicesSku = 'S0'
param namedValues = []
param openAIInstances = []
param docIntelInstances = []
param lock = {
  name: null
  kind: 'None'
}
param tags = {
  Environment: 'Test'
  Purpose: 'Demo'
}

// Backend configuration
param backendConfig = [
  {
    name: 'eastus2-primary'
    priority: 1
    location: 'eastus2'
    chat: {
      sku: 'GlobalStandard'
      capacity: 10
      modelName: 'gpt-4o'
      version: '2024-08-06'
    }
    reasoning: {
      sku: 'GlobalStandard'
      capacity: 10
      modelName: 'o1'
      version: '2025-01-01-preview'
    }
    embedding: {
      sku: 'Standard'
      capacity: 10
      modelName: 'text-embedding-3-large'
      version: '1'
    }
  }
]

*/
