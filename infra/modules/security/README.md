# Documentation for the Bicep modules in this directory



## Table of Contents
- [aca](#aca)
  - [Parameters](#parameters)
  - [Outputs](#outputs)
  - [Snippets](#snippets)
- [appregistration](#appregistration)
  - [Parameters](#parameters-1)
  - [Outputs](#outputs-1)
  - [Snippets](#snippets-1)
- [appupdate](#appupdate)
  - [Parameters](#parameters-2)
  - [Outputs](#outputs-2)
  - [Snippets](#snippets-2)
- [bicepconfig](#bicepconfig)
  - [Parameters](#parameters-3)
  - [Outputs](#outputs-3)
  - [Snippets](#snippets-3)

# aca

## Outputs

Name | Type | Description
---- | ---- | -----------
identityPrincipalId | string |
name | string |
uri  | string |
imageName | string |
identityResourceId | string |

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/security/aca.json"
    },
    "parameters": {}
}
```
# appregistration

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
cloudEnvironment | No       | Specifies the name of cloud environment to run this deployment in.
audiences      | No       | Audience uris for public and national clouds
webAppIdentityId | Yes      | Specifies the ID of the user-assigned managed identity.
clientAppName  | Yes      | Specifies the unique name for the client application.
clientAppDisplayName | Yes      | Specifies the display name for the client application
clientAppScopes | No       | Specifies the scopes that the client application requires.
serviceManagementReference | No       |
issuer         | Yes      |
webAppEndpoint | Yes      |

### cloudEnvironment

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Specifies the name of cloud environment to run this deployment in.

- Default value: `[environment().name]`

### audiences

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Audience uris for public and national clouds

- Default value: `@{AzureCloud=; AzureUSGovernment=; USNat=; USSec=; AzureChinaCloud=}`

### webAppIdentityId

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Specifies the ID of the user-assigned managed identity.

### clientAppName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Specifies the unique name for the client application.

### clientAppDisplayName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Specifies the display name for the client application

### clientAppScopes

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Specifies the scopes that the client application requires.

- Default value: `User.Read offline_access openid profile`

### serviceManagementReference

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)



### issuer

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)



### webAppEndpoint

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)



## Outputs

Name | Type | Description
---- | ---- | -----------
clientAppId | string |
clientSpId | string |

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/security/appregistration.json"
    },
    "parameters": {
        "cloudEnvironment": {
            "value": "[environment().name]"
        },
        "audiences": {
            "value": {
                "AzureCloud": {
                    "uri": "api://AzureADTokenExchange"
                },
                "AzureUSGovernment": {
                    "uri": "api://AzureADTokenExchangeUSGov"
                },
                "USNat": {
                    "uri": "api://AzureADTokenExchangeUSNat"
                },
                "USSec": {
                    "uri": "api://AzureADTokenExchangeUSSec"
                },
                "AzureChinaCloud": {
                    "uri": "api://AzureADTokenExchangeChina"
                }
            }
        },
        "webAppIdentityId": {
            "value": ""
        },
        "clientAppName": {
            "value": ""
        },
        "clientAppDisplayName": {
            "value": ""
        },
        "clientAppScopes": {
            "value": [
                "User.Read",
                "offline_access",
                "openid",
                "profile"
            ]
        },
        "serviceManagementReference": {
            "value": ""
        },
        "issuer": {
            "value": ""
        },
        "webAppEndpoint": {
            "value": ""
        }
    }
}
```

## Default Values


- **cloudEnvironment**: [environment().name]

- **audiences**: @{AzureCloud=; AzureUSGovernment=; USNat=; USSec=; AzureChinaCloud=}

- **clientAppScopes**: User.Read offline_access openid profile
# appupdate

Creates an Azure Container Apps Auth Config using Microsoft Entra as Identity Provider.

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
containerAppName | Yes      | The name of the container apps resource within the current resource group scope
clientId       | Yes      | The client ID of the Microsoft Entra application.
openIdIssuer   | Yes      |
includeTokenStore | No       | Enable token store for the Container App.
blobContainerUri | No       | The URI of the Azure Blob Storage container to be used for token storage.
appIdentityResourceId | No       | The resource ID of the managed identity to be used for accessing the Azure Blob Storage.

### containerAppName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

The name of the container apps resource within the current resource group scope

### clientId

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

The client ID of the Microsoft Entra application.

### openIdIssuer

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)



### includeTokenStore

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Enable token store for the Container App.

- Default value: `False`

### blobContainerUri

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

The URI of the Azure Blob Storage container to be used for token storage.

### appIdentityResourceId

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

The resource ID of the managed identity to be used for accessing the Azure Blob Storage.

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/security/appupdate.json"
    },
    "parameters": {
        "containerAppName": {
            "value": ""
        },
        "clientId": {
            "value": ""
        },
        "openIdIssuer": {
            "value": ""
        },
        "includeTokenStore": {
            "value": false
        },
        "blobContainerUri": {
            "value": ""
        },
        "appIdentityResourceId": {
            "value": ""
        }
    }
}
```
# bicepconfig

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/security/bicepconfig.json"
    },
    "parameters": {}
}
```
