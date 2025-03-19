# Documentation for the Bicep modules in this directory



## Table of Contents
- [aifoundry](#aifoundry)
  - [Parameters](#parameters)
  - [Outputs](#outputs)
  - [Snippets](#snippets)
- [docintelligence](#docintelligence)
  - [Parameters](#parameters-1)
  - [Outputs](#outputs-1)
  - [Snippets](#snippets-1)
- [mais](#mais)
  - [Parameters](#parameters-2)
  - [Outputs](#outputs-2)
  - [Snippets](#snippets-2)
- [openai](#openai)
  - [Parameters](#parameters-3)
  - [Outputs](#outputs-3)
  - [Snippets](#snippets-3)

# aifoundry

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
location       | Yes      | Azure region of the deployment
tags           | Yes      | Tags to add to the resources
aiFoundryName  | Yes      | Name of the AI Foundry instance
aiFoundryFriendlyName | No       | Display name for the AI Foundry instance
aiFoundryDescription | Yes      | Description for the AI Foundry instance
applicationInsightsId | Yes      | Resource ID of the Application Insights resource for diagnostics logs
containerRegistryId | Yes      | Resource ID of the Container Registry for storing docker images
keyVaultId     | Yes      | Resource ID of the Key Vault for storing connection strings
storageAccountId | Yes      | Resource ID of the Storage Account for experimentation outputs
aiServicesId   | Yes      | Resource ID of the AI Services resource
aiServicesKey  | Yes      | API key for the AI Services resource
aiServicesTarget | Yes      | Target endpoint of the AI Services
aiFoundryProjectName | No       | Name of the AI Foundry project (evaluations)

### location

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Azure region of the deployment

### tags

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Tags to add to the resources

### aiFoundryName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Name of the AI Foundry instance

### aiFoundryFriendlyName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Display name for the AI Foundry instance

- Default value: `[parameters('aiFoundryName')]`

### aiFoundryDescription

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Description for the AI Foundry instance

### applicationInsightsId

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Resource ID of the Application Insights resource for diagnostics logs

### containerRegistryId

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Resource ID of the Container Registry for storing docker images

### keyVaultId

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Resource ID of the Key Vault for storing connection strings

### storageAccountId

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Resource ID of the Storage Account for experimentation outputs

### aiServicesId

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Resource ID of the AI Services resource

### aiServicesKey

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

API key for the AI Services resource

### aiServicesTarget

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Target endpoint of the AI Services

### aiFoundryProjectName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Name of the AI Foundry project (evaluations)

- Default value: `evaluations`

## Outputs

Name | Type | Description
---- | ---- | -----------
aiFoundryId | string |
aiFoundryPrincipalId | string |
aiFoundryConnectionString | string |

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/ai/aifoundry.json"
    },
    "parameters": {
        "location": {
            "value": ""
        },
        "tags": {
            "value": {}
        },
        "aiFoundryName": {
            "value": ""
        },
        "aiFoundryFriendlyName": {
            "value": "[parameters('aiFoundryName')]"
        },
        "aiFoundryDescription": {
            "value": ""
        },
        "applicationInsightsId": {
            "value": ""
        },
        "containerRegistryId": {
            "value": ""
        },
        "keyVaultId": {
            "value": ""
        },
        "storageAccountId": {
            "value": ""
        },
        "aiServicesId": {
            "value": ""
        },
        "aiServicesKey": {
            "value": ""
        },
        "aiServicesTarget": {
            "value": ""
        },
        "aiFoundryProjectName": {
            "value": "evaluations"
        }
    }
}
```

## Default Values


- **aiFoundryFriendlyName**: [parameters('aiFoundryName')]

- **aiFoundryProjectName**: evaluations
# docintelligence

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
location       | Yes      | Azure region of the deployment
tags           | Yes      | Tags to add to the resources
aiServiceName  | Yes      | Name of the AI service
aiServiceSkuName | No       | AI service SKU

### location

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Azure region of the deployment

### tags

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Tags to add to the resources

### aiServiceName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Name of the AI service

### aiServiceSkuName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

AI service SKU

- Default value: `S0`

- Allowed values: `S0`

## Outputs

Name | Type | Description
---- | ---- | -----------
aiServicesId | string |
aiServicesEndpoint | string |
aiServiceDocIntelligenceEndpoint | string |
aiServicesName | string |
aiServicesPrincipalId | string |
aiServicesKey | string |

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/ai/docintelligence.json"
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
            "value": "S0"
        }
    }
}
```

## Default Values


- **aiServiceSkuName**: S0
# mais

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
location       | Yes      | Azure region of the deployment
tags           | Yes      | Tags to add to the resources
aiServiceName  | Yes      | Name of the AI service
aiServiceSkuName | No       | AI service SKU

### location

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Azure region of the deployment

### tags

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Tags to add to the resources

### aiServiceName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Name of the AI service

### aiServiceSkuName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

AI service SKU

- Default value: `S0`

- Allowed values: `S0`

## Outputs

Name | Type | Description
---- | ---- | -----------
aiServicesId | string |
aiServicesEndpoint | string |
aiServicesName | string |
aiServicesPrincipalId | string |
aiServicesPrimaryKey | string |

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/ai/mais.json"
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
            "value": "S0"
        }
    }
}
```

## Default Values


- **aiServiceSkuName**: S0
# openai

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
location       | Yes      | Azure region of the deployment
tags           | Yes      | Tags to add to the resources
aiServiceName  | Yes      | Name of the AI service
aiServiceSkuName | No       | AI service SKU
chatCompletionModels | No       | List of chat completion models to be deployed to the OpenAI account.
embeddingModel | No       | List of embedding models to be deployed to the OpenAI account.

### location

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Azure region of the deployment

### tags

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Tags to add to the resources

### aiServiceName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Name of the AI service

### aiServiceSkuName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

AI service SKU

- Default value: `S0`

- Allowed values: `S0`

### chatCompletionModels

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

List of chat completion models to be deployed to the OpenAI account.

### embeddingModel

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

List of embedding models to be deployed to the OpenAI account.

- Default value: `@{name=text-embedding-ada-002; version=2; skuName=Standard; capacity=250}`

## Outputs

Name | Type | Description
---- | ---- | -----------
aiServicesId | string |
aiServicesEndpoint | string |
aiServicesName | string |
aiServicesPrincipalId | string |
aiServicesKey | string |

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/modules/ai/openai.json"
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
            "value": "S0"
        },
        "chatCompletionModels": {
            "value": [
                {
                    "name": "gpt-4o",
                    "version": "2024-08-06",
                    "skuName": "GlobalStandard",
                    "capacity": 25
                }
            ]
        },
        "embeddingModel": {
            "value": {
                "name": "text-embedding-ada-002",
                "version": "2",
                "skuName": "Standard",
                "capacity": 250
            }
        }
    }
}
```

## Default Values


- **aiServiceSkuName**: S0

- **chatCompletionModels**: @{name=gpt-4o; version=2024-08-06; skuName=GlobalStandard; capacity=25}

- **embeddingModel**: @{name=text-embedding-ada-002; version=2; skuName=Standard; capacity=250}
