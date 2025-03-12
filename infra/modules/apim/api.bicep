@description('The name of the API to be appended in resource names.')
param name string

@description('The description for the API.')
param apiDescription string

@description('The display name for the API.')
param apiDisplayName string

@description('The path for the API.')
param apiPath string

@description('The name of the existing API Management (APIM) service.')
param apimName string

@description('The Text Content of the Policy.')
param policyContent string

@description('The URL for the API specification.')
param apiSpecURL string
@description('The name of the subscription for the API.')
param apiSubscriptionName string
@description('The description of the subscription for the API.')
param apiSubscriptionDescription string

resource _apim 'Microsoft.ApiManagement/service@2022-08-01' existing = {
  name: apimName
}

resource api 'Microsoft.ApiManagement/service/apis@2022-08-01' = {
  name: name
  parent: _apim
  properties: {
    apiType: 'http'
    description: apiDescription
    displayName: apiDisplayName
    format: 'openapi-link'
    path: apiPath
    protocols: [
      'https'
    ]
    subscriptionRequired: true
    subscriptionKeyParameterNames: {
      header: 'api-key'
      query: 'api-key'
    }
    type: 'http'
    value: apiSpecURL
  }
}

resource apiPolicy 'Microsoft.ApiManagement/service/apis/policies@2023-09-01-preview' = {
  name: 'policy'
  parent: api
  properties: {
    format: 'rawxml'
    value: policyContent
  }
}


resource apiSubscription 'Microsoft.ApiManagement/service/subscriptions@2023-09-01-preview' = {
  name: apiSubscriptionName
  parent: _apim
  properties: {
    allowTracing: true
    displayName: apiSubscriptionDescription
    scope: '/apis/${api.id}'
    state: 'active'
  }
}

output apiPath string = api.properties.path
output apiId string = api.id
output apiScope string = '/apis/${api.id}'
output apiSubscriptionId string = apiSubscription.id
output apiSubscriptionName string = apiSubscription.name
// output apiSubscriptionKey string = apiSubscription.properties.primaryKey
