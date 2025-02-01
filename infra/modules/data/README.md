# Documentation for the Bicep modules in this directory



## Table of Contents
- [cosmos-mongo-ru](#cosmos-mongo-ru)
  - [Parameters](#parameters)
  - [Outputs](#outputs)
  - [Snippets](#snippets)
- [cosmos-mongo](#cosmos-mongo)
  - [Parameters](#parameters-1)
  - [Outputs](#outputs-1)
  - [Snippets](#snippets-1)
- [search](#search)
  - [Parameters](#parameters-2)
  - [Outputs](#outputs-2)
  - [Snippets](#snippets-2)
- [storage](#storage)
  - [Parameters](#parameters-3)
  - [Outputs](#outputs-3)
  - [Snippets](#snippets-3)

# cosmos-mongo-ru

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
location       | Yes      | Azure region of the deployment
tags           | Yes      | Tags to add to the resources
aiServiceName  | Yes      | Name of the Mongo cluster

### location

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Azure region of the deployment

### tags

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Tags to add to the resources

### aiServiceName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Name of the Mongo cluster

## Outputs

Name | Type | Description
---- | ---- | -----------
mongoClusterId | string |
mongoClusterName | string |
mongoConnectionString | string |

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/data/cosmos-mongo-ru.json"
    },
    "parameters": {
        "location": {
            "value": ""
        },
        "tags": {
            "value": {}
        },
        "aiServiceName": {
            "value": ""
        }
    }
}
```
# cosmos-mongo

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
location       | Yes      | Azure region of the deployment
tags           | Yes      | Tags to add to the resources
aiServiceName  | Yes      | Name of the Mongo cluster
cosmosAdministratorUsername | No       | Administrator username for the Mongo cluster
cosmosAdministratorPassword | Yes      | Admin password for the cluster

### location

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Azure region of the deployment

### tags

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Tags to add to the resources

### aiServiceName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Name of the Mongo cluster

### cosmosAdministratorUsername

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Administrator username for the Mongo cluster

- Default value: `adminuser`

### cosmosAdministratorPassword

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Admin password for the cluster

## Outputs

Name | Type | Description
---- | ---- | -----------
mongoClusterId | string |
mongoClusterName | string |
mongoConnectionString | string |

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/data/cosmos-mongo.json"
    },
    "parameters": {
        "location": {
            "value": ""
        },
        "tags": {
            "value": {}
        },
        "aiServiceName": {
            "value": ""
        },
        "cosmosAdministratorUsername": {
            "value": "adminuser"
        },
        "cosmosAdministratorPassword": {
            "reference": {
                "keyVault": {
                    "id": ""
                },
                "secretName": ""
            }
        }
    }
}
```

## Default Values


- **cosmosAdministratorUsername**: adminuser
# search

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
location       | Yes      | Azure region of the deployment
tags           | Yes      | Tags to add to the resources
aiServiceName  | Yes      | Name of the Search service
aiServiceSkuName | No       | Search service SKU

### location

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Azure region of the deployment

### tags

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Tags to add to the resources

### aiServiceName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Name of the Search service

### aiServiceSkuName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Search service SKU

- Default value: `basic`

- Allowed values: `basic`

## Outputs

Name | Type | Description
---- | ---- | -----------
searchServiceIdentityPrincipalId | string |
searchServiceId | string |
searchServiceName | string |
searchServicePrimaryKey | string |
searchServiceEndpoint | string |

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/data/search.json"
    },
    "parameters": {
        "location": {
            "value": ""
        },
        "tags": {
            "value": {}
        },
        "aiServiceName": {
            "value": ""
        },
        "aiServiceSkuName": {
            "value": "basic"
        }
    }
}
```

## Default Values


- **aiServiceSkuName**: basic
# storage

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
location       | Yes      | Azure region of the deployment
tags           | Yes      | Tags to add to the resources
aiServiceName  | Yes      | Name of the Storage account
aiServiceSkuName | No       | Storage SKU

### location

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Azure region of the deployment

### tags

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Tags to add to the resources

### aiServiceName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Name of the Storage account

### aiServiceSkuName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Storage SKU

- Default value: `Standard_LRS`

- Allowed values: `Standard_LRS`, `Standard_GRS`, `Standard_RAGRS`, `Standard_ZRS`

## Outputs

Name | Type | Description
---- | ---- | -----------
storageAccountId | string |
storageAccountName | string |
storageAccountPrimaryKey | string |
storageAccountPrimaryConnectionString | string |

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/data/storage.json"
    },
    "parameters": {
        "location": {
            "value": ""
        },
        "tags": {
            "value": {}
        },
        "aiServiceName": {
            "value": ""
        },
        "aiServiceSkuName": {
            "value": "Standard_LRS"
        }
    }
}
```

## Default Values


- **aiServiceSkuName**: Standard_LRS
