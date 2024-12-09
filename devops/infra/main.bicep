//tmp

@description('The location into which the resources should be deployed.')
param location string

// Deploy Cognitive Services: doc-extract
module docIntelligence 'modules/cognitive-doc-extract.bicep' = {
  name: 'cog-doc-extract'
  params: {
    location: location
  }
}

// Deploy Cognitive Services: MAIS
module multiServiceCogServices 'modules/cognitive-mais.bicep' = {
  name: 'cog-mais'
  params: {
    location: location
  }
}

// Deploy Cognitive Services: OAI
module cognitiveOpenAi 'modules/cognitive-oai.bicep' = {
  name: 'cog-oai'
  params: {
    location: location
  }
}

// Deploy MongoDB Cluster
module cosmosMongoDb 'modules/mongodb-cluster.bicep' = {
  name: 'mongo-cluster'
  params: {
    // This resource is in southindia, so we hard-code that
    location: 'southindia'
  }
}

// Deploy Application Insights
module appInsights 'modules/appinsights.bicep' = {
  name: 'app-insights'
  params: {
    location: 'eastus'
    workspaceResourceId: '/subscriptions/28d2df62-e322-4b25-b581-c43b94bd2607/resourceGroups/DefaultResourceGroup-EUS/providers/Microsoft.OperationalInsights/workspaces/DefaultWorkspace-28d2df62-e322-4b25-b581-c43b94bd2607-EUS'
  }
}

// Deploy Search service
module searchService 'modules/search.bicep' = {
  name: 'search-svc'
  params: {
    location: 'eastus'
  }
}

// Deploy Storage account
module storage 'modules/storage.bicep' = {
  name: 'storage-acct'
  params: {
    location: 'eastus'
  }
}
