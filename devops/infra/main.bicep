// Execute this main file to deploy Prior Authorization related resources in a basic configuration

// Parameters
@minLength(2)
@maxLength(12)
@description('Name for the PriorAuth resource and used to derive the name of dependent resources.')
param priorAuthName string = 'priorAuth'

@description('Set of tags to apply to all resources.')
param tags object = {}

@description('Admin password for the cluster')
@secure()
param cosmosAdministratorPassword string

// @description('Resource name of the virtual network to deploy the resource into.')
// param vnetName string

// @description('Resource group name of the virtual network to deploy the resource into.')
// param vnetRgName string

// @description('Name of the subnet to deploy into.')
// param subnetName string

@description('The location into which the resources should be deployed.')
param location string = resourceGroup().location

// @minLength(2)
// @maxLength(10)
// @description('Prefix for all resource names.')
// param prefix string

// Variables
var name = toLower('${priorAuthName}')
var uniqueSuffix = substring(uniqueString(resourceGroup().id), 0, 7)

// var vnetResourceId = '/subscriptions/${subscription().subscriptionId}/resourceGroups/${vnetRgName}/providers/Microsoft.Network/virtualNetworks/${vnetName}'
// var subnetResourceId = '${vnetResourceId}/subnets/${subnetName}'
var storageServiceName = toLower(replace('storage-${name}-${uniqueSuffix}', '-', ''))

// Deploy Cognitive Services: doc-extract
module docIntelligence 'tmpmodules/docintelligence.bicep' = {
  name: 'doc-intelligence-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'doc-intelligence-${name}-${uniqueSuffix}'
    location: location
    tags: tags
    aiServiceSkuName: 'S0'
  }
}

module multiAccountAiServices 'tmpmodules/cs-mais.bicep' = {
  name: 'multiservice-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'multiservice-${name}-${uniqueSuffix}'
    location: location
    tags: tags
    aiServiceSkuName: 'S0' // or another allowed SKU if appropriate
  }
}

// Deploy Cognitive Services: OpenAI
module openAiService 'tmpmodules/cs-openai.bicep' = {
  name: 'openai-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'openai-${name}-${uniqueSuffix}'
    location: location
    tags: tags
    aiServiceSkuName: 'S0'
  }
}

// Deploy Search Service
module searchService 'tmpmodules/search.bicep' = {
  name: 'search-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'search-${name}-${uniqueSuffix}'
    location: location
    tags: tags
    aiServiceSkuName: 'basic'
  }
}

module storageAccount 'tmpmodules/storage.bicep' = {
  name: 'storage-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: storageServiceName
    location: location
    tags: tags
    aiServiceSkuName: 'Standard_LRS'
  }
}

// Deploy Application Insights
module appInsights 'tmpmodules/appinsights.bicep' = {
  name: 'appinsights-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'appinsights-${name}-${uniqueSuffix}'
    location: location
    tags: tags
  }
}

// Deploy Cosmos DB Mongo Cluster
module cosmosDb 'tmpmodules/cosmos-mongo.bicep' = {
  name: 'cosmosdb-${name}-${uniqueSuffix}-deployment'
  params: {
    aiServiceName: 'cosmosdb-${name}-${uniqueSuffix}'
    location: location
    tags: tags
    cosmosAdministratorPassword: cosmosAdministratorPassword
  }
}
