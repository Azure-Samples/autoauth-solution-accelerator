@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('Name of the Mongo cluster')
param aiServiceName string

@description('Administrator username for the Mongo cluster')
param cosmosAdministratorUsername string = 'adminuser' // Default username, can be overridden

@description('Admin password for the cluster')
@secure()
param cosmosAdministratorPassword string

var mongoNameCleaned = replace(aiServiceName, '-', '')

resource mongoCluster 'Microsoft.DocumentDB/mongoClusters@2024-07-01' = {
  name: mongoNameCleaned
  location: location
  tags: tags
  properties: {
    administrator: {
      userName: cosmosAdministratorUsername
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

output mongoClusterId string = mongoCluster.id
output mongoClusterName string = mongoCluster.name

// Variable: Encoded Cosmos Administrator Password
var encodedPassword = uriComponent(cosmosAdministratorPassword)

output mongoConnectionString string = 'mongodb+srv://${cosmosAdministratorUsername}:${encodedPassword}@${mongoNameCleaned}.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000'
