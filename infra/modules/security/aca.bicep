// resource acaIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
//   name: identityName
//   location: location
// }

output identityPrincipalId string = '48275e14-c183-4fd6-8081-4301098be101' // client ID <-- use this one
// output identityPrincipalId string = '1a351ceb-aa4d-4b1d-91c5-d95f593bb3ae' // object (principal) ID
output name string = 'pe-fe-priorauth-liocb4m'
output uri string = 'https://pe-fe-priorauth-liocb4m.blackgrass-c8d1222d.eastus2.azurecontainerapps.io'
output imageName string = 'gbb-ai-hls-factory-prior-auth/frontend-local-dev:azd-deploy-1741105197'
output identityResourceId string = '/subscriptions/63862159-43c8-47f7-9f6f-6c63d56b0e17/resourcegroups/rg-priorauth-eastus2-local-dev/providers/microsoft.managedidentity/userassignedidentities/uai-app-priorauth-liocb4m'
