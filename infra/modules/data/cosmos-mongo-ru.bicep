@description('Azure region of the deployment')
param location string

@description('Tags to add to the resources')
param tags object

@description('Name of the Mongo cluster')
param aiServiceName string

// @description('Administrator username for the Mongo cluster')
// param cosmosAdministratorUsername string = 'adminuser' // Default username, can be overridden

// @description('Admin password for the cluster')
// @secure()
// param cosmosAdministratorPassword string

var mongoNameCleaned = replace(aiServiceName, '-', '')

resource mongoCluster 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: mongoNameCleaned
  location: location
  tags: tags
  kind: 'MongoDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    // administrator: {
    //   userName: cosmosAdministratorUsername
    //   password: cosmosAdministratorPassword
    // }
    apiProperties: {
      serverVersion: '7.0'
    }

    capabilities: [
      {
        name: 'EnableMongo'
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    publicNetworkAccess: 'Enabled'
  }
}



output mongoClusterId string = mongoCluster.id
output mongoClusterName string = mongoCluster.name

// Variable: Encoded Cosmos Administrator Password
// var encodedPassword = uriComponent(cosmosAdministratorPassword)

// output mongoConnectionString string = 'mongodb+srv://${cosmosAdministratorUsername}:${encodedPassword}@${mongoNameCleaned}.mongo.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000'
output mongoConnectionString string = mongoCluster.listConnectionStrings().connectionStrings[0].connectionString
