# Create the Azure AD application.
#  Example web redirect uri: "https://mycontainer.somerevision.westus.azurecontainerapps.io/.auth/login/aad/callback"
application=$(az ad app create --display-name $AzureADApplicationName \
                               --web-redirect-uris $AzureADApplicationRedirectUri \
                               --enable-id-token-issuance true \
                               --sign-in-audience AzureADMyOrg )


applicationObjectId=$(jq -r '.id' <<< "$application")
applicationClientId=$(jq -r '.appId' <<< "$application")

az ad app update --id $applicationObjectId --identifier-uris "api://$applicationClientId"

# Generate a new GUID for the oauth2PermissionScope id
newScopeId=$(uuidgen)
jsonApiScopes='
{
    "oauth2PermissionScopes": [
        {
            "adminConsentDescription": "Allow the application to access priorAuth-container-app on behalf of the signed-in user.",
            "adminConsentDisplayName": "Access priorAuth-container-app",
            "id": "'$newScopeId'",
            "isEnabled": true,
            "type": "User",
            "userConsentDescription": "Allow the application to access container-app on your behalf.",
            "userConsentDisplayName": "Access priorAuth-container-app",
            "value": "user_impersonation"
        }
    ]
}'
apiScopes=$(echo $jsonApiScopes | jq -c '.')

# Add the oauth permission scope to the application.
az ad app update --id $applicationClientId --set api=$apiScopes --verbose

# Add User.Read permission to the application.
az ad app permission add --id $applicationObjectId \
                         --api 00000003-0000-0000-c000-000000000000 \
                         --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope

# # Grant admin consent for the required permissions.
az ad app permission admin-consent --id $applicationObjectId

# # Create a service principal for the application.
# servicePrincipal=$(az ad sp create --id $applicationObjectId)
# servicePrincipalObjectId=$(jq -r '.id' <<< "$servicePrincipal")

# # Save the important properties as depoyment script outputs.
outputJson=$(jq -n \
                --arg applicationObjectId "$applicationObjectId" \
                --arg applicationClientId "$applicationClientId" \
                '{applicationObjectId: $applicationObjectId, applicationClientId: $applicationClientId}' )
                # --arg servicePrincipalObjectId "$servicePrincipalObjectId" \

# Add the applicationObjectId and applicationClientId to azd environment
azd env set AZURE_AD_APP_OBJECT_ID $applicationObjectId
azd env set AZURE_AD_APP_CLIENT_ID $applicationClientId

if [ -n "$AZ_SCRIPTS_OUTPUT_PATH" ]; then
    echo $outputJson > $AZ_SCRIPTS_OUTPUT_PATH
else
    echo $outputJson
fi
