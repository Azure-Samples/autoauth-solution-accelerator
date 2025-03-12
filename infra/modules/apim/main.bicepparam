using './main.bicep'

param name = 'aauth-localtest2'
param location = 'eastus2'

param diagnosticSettings = [
  {
    // eventHubAuthorizationRuleResourceId: '<eventHubAuthorizationRuleResourceId>'
    // eventHubName: '<eventHubName>'
    // storageAccountResourceId: '<storageAccountResourceId>'
    workspaceResourceId: '/subscriptions/63862159-43c8-47f7-9f6f-6c63d56b0e17/resourcegroups/apim-sandbox-ncus/providers/microsoft.operationalinsights/workspaces/apim-ncus-law'
  }
]
param localClientId = 'd4215af3-a69c-4640-9004-3cfc07dc032f'
param appClientId = '66dbac08-9f73-4a2c-88ca-27b0c1f30bdc'
param apimPublisherEmail = 'noreply@microsoft.com'
param apimPublisherName = 'Jin Lee Local Testing'
param sku = 'BasicV2'
param namedValues = [
  {
    displayName: 'exampleNamedValue1'
    name: 'exampleNamedValue1'
    value: 'Value1'
    secret: false
  }
  {
    displayName: 'exampleNamedValue2'
    name: 'exampleNamedValue2'
    value: 'Value2'
    secret: true
  }
]
param openAIInstances = [
  {
    name: 'openai1'
    url: 'https://openai1-mitqecds2lchm.openai.azure.com/'
    weight: 80
    priority: 1
  }
  {
    name: 'openai2'
    url: 'https://openai2-mitqecds2lchm.openai.azure.com/'
    weight: 10
    priority: 2
  }
  {
    name: 'openai3'
    url: 'https://openai3-mitqecds2lchm.openai.azure.com/'
    weight: 10
    priority: 2
  }
]
