@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('Name of the Mongo cluster')
param aiServiceName string

@description('Admin password for the cluster')
param cosmosAdministratorPassword string

var mongoNameCleaned = replace(aiServiceName, '-', '')

resource mongoCluster 'Microsoft.DocumentDB/mongoClusters@2024-07-01' = {
  name: mongoNameCleaned
  location: location
  tags: tags
  properties: {
    administrator: {
      userName: 'adminuser'
      password: cosmosAdministratorPassword
    }
    serverVersion: '7.0'
    compute: {
      tier: 'M30'
    }
    storage: {
      sizeGb: 32
    }
    sharding: {
      shardCount: 1
    }
    highAvailability: {
      targetMode: 'Disabled'
    }
    publicNetworkAccess: 'Enabled'
    previewFeatures: [
      'GeoReplicas'
    ]
  }
}

// // Retrieve keys and connection strings
// var clusterKeys = mongoCluster.listKeys()
// var clusterConnStrings = mongoCluster.listConnectionStrings()

// // Assume the first connection string is the primary connection string
// var primaryConnectionString = clusterConnStrings.connectionStrings[0].connectionString
// var endpointPortPart = split(primaryConnectionString, '@')[1]
// var cosmosEndpoint = split(endpointPortPart, ':')[0]

// // Extract the primary key from clusterKeys
// var cosmosDatabaseKey = clusterKeys.primaryKey

output mongoClusterId string = mongoCluster.id
output mongoClusterName string = mongoCluster.name
// output cosmosEndpoint string = cosmosEndpoint
// output cosmosDatabaseKey string = cosmosDatabaseKey
// output cosmosConnectionString string = primaryConnectionString
