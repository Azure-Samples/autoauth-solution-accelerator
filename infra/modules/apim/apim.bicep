
param tags object = {}
@description('List of OpenAI resources to create. Add pairs of name and location.')
param openAIConfig array = []

@description('Deployment Name')
param openAIDeploymentName string

@description('Azure OpenAI Sku')
@allowed([
  'S0'
])
param openAISku string = 'S0'

@description('Model Name')
param openAIModelName string

@description('Model Version')
param openAIModelVersion string

@description('Model Capacity')
param openAIModelCapacity int = 20

@description('The name of the API Management resource')
param apimResourceName string

@description('Location for the APIM resource')
param apimResourceLocation string = resourceGroup().location

@description('The pricing tier of this API Management service')
@allowed([
  'Consumption'
  'Developer'
  'Basic'
  'Basicv2'
  'Standard'
  'Standardv2'
  'Premium'
])
param apimSku string = 'Consumption'

@description('The instance size of this API Management service.')
@allowed([
  0
  1
  2
])
param apimSkuCount int = 1

@description('The email address of the owner of the service')
param apimPublisherEmail string = 'noreply@microsoft.com'

@description('The name of the owner of the service')
param apimPublisherName string = 'Microsoft'

@description('The name of the APIM API for OpenAI API')
param openAIAPIName string = 'openai'

@description('The relative path of the APIM API for OpenAI API')
param openAIAPIPath string = 'openai'

@description('The display name of the APIM API for OpenAI API')
param openAIAPIDisplayName string = 'OpenAI'

@description('The description of the APIM API for OpenAI API')
param openAIAPIDescription string = 'Azure OpenAI API inferencing API'

@description('Full URL for the OpenAI API spec')
param openAIAPISpecURL string = 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/specification/cognitiveservices/data-plane/AzureOpenAI/inference/stable/2024-02-01/inference.json'

@description('The name of the APIM Subscription for OpenAI API')
param openAISubscriptionName string = 'openai-subscription'

@description('The description of the APIM Subscription for OpenAI API')
param openAISubscriptionDescription string = 'OpenAI Subscription'


@description('Embeddings Model Name')
param embeddingsModelName string

@description('Embeddings Model Version')
param embeddingsModelVersion string = '1'

param deploymentsConfig array = []
// Local Test and App Client ID Parameters
param DisableLocalTestAccount bool = false
@description('The client ID of the local test account')
param localClientId string = '00000000-0000-0000-0000-000000000000'
param appClientId string = '00000000-0000-0000-0000-000000000000'

var effectiveLocalClientId = DisableLocalTestAccount ? appClientId : localClientId

// Common Variables
var resourceSuffix = uniqueString(subscription().id, resourceGroup().id)


//===========================================================
// Section: API Management Core Resources
//===========================================================

resource apimService 'Microsoft.ApiManagement/service@2023-09-01-preview' = {
  name: '${apimResourceName}-${resourceSuffix}'
  location: apimResourceLocation
  sku: {
    name: apimSku
    capacity: (apimSku == 'Consumption') ? 0 : ((apimSku == 'Developer') ? 1 : apimSkuCount)
  }
  properties: {
    publisherEmail: apimPublisherEmail
    publisherName: apimPublisherName
  }
  identity: {
    type: 'SystemAssigned'
  }
}

module openAIAPI 'apis/openai/main.bicep' = {
  name: 'api-openai-${apimResourceName}-${resourceSuffix}'
  scope: resourceGroup()
  params: {

    apimName: '${apimResourceName}-${resourceSuffix}'
    localClientId: effectiveLocalClientId
    appClientId: appClientId
    apiName: openAIAPIName
    apiPath: openAIAPIPath
    apiDescription: openAIAPIDescription
    apiDisplayName: openAIAPIDisplayName
    openAIAPISpecURL: openAIAPISpecURL
    deploymentsConfig: deploymentsConfig
    openAISubscriptionName: openAISubscriptionName
    openAISubscriptionDescription: openAISubscriptionDescription
    embeddingsModelName: embeddingsModelName
    embeddingsModelVersion: embeddingsModelVersion
    chatCompletionModelName: openAIModelName
    chatCompletionModelVersion: openAIModelVersion
    aiServiceSkuName: openAISku
    tags: tags
  }
}

output deployer object = deployer()
output apimServiceId string = apimService.id
output apimResourceGatewayURL string = apimService.properties.gatewayUrl
// disable-next-line outputs-should-not-contain-secrets
output apimSubscriptionKey string = openAIAPI.outputs.apiSubscriptionKey
