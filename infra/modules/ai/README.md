# Documentation for the Bicep modules in this directory



## Table of Contents
- [docintelligence](#docintelligence)
  - [Parameters](#parameters)
  - [Outputs](#outputs)
  - [Snippets](#snippets)
- [mais](#mais)
  - [Parameters](#parameters-1)
  - [Outputs](#outputs-1)
  - [Snippets](#snippets-1)
- [openai](#openai)
  - [Parameters](#parameters-2)
  - [Outputs](#outputs-2)
  - [Snippets](#snippets-2)

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
