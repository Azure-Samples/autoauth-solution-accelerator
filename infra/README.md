# Documentation for the Bicep modules in this directory



## Table of Contents
- [main](#main)
  - [Parameters](#parameters)
  - [Outputs](#outputs)
  - [Snippets](#snippets)
- [resources](#resources)
  - [Parameters](#parameters-1)
  - [Outputs](#outputs-1)
  - [Snippets](#snippets-1)

# main

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
environmentName | Yes      | Name of the environment that can be used as part of naming resource convention
location       | Yes      | Primary location for all resources. Not all regions are supported due to OpenAI limitations
frontendExists | No       | Flag to indicate if Frontend app image exists. This is managed by AZD
backendExists  | No       | Flag to indicate if Backend app image exists. This is managed by AZD
priorAuthName  | No       | Name for the PriorAuth resource and used to derive the name of dependent resources.
tags           | No       | Tags to be applied to all resources
openAiApiVersion | No       | API Version of the OpenAI API
chatCompletionModels | No       | List of completion models to be deployed to the OpenAI account.
embeddingModel | No       | List of embedding models to be deployed to the OpenAI account.
embeddingModelDimension | No       | Embedding model size for the OpenAI Embedding deployment
storageBlobContainerName | No       | Storage Blob Container name to land the files for Prior Auth

### environmentName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Name of the environment that can be used as part of naming resource convention

### location

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Primary location for all resources. Not all regions are supported due to OpenAI limitations

- Allowed values: `australiaeast`, `canadaeast`, `eastus`, `eastus2`, `francecentral`, `japaneast`, `norwayeast`, `polandcentral`, `southindia`, `swedencentral`, `switzerlandnorth`, `uksouth`, `westus3`

### frontendExists

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Flag to indicate if Frontend app image exists. This is managed by AZD

- Default value: `False`

### backendExists

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Flag to indicate if Backend app image exists. This is managed by AZD

- Default value: `False`

### priorAuthName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Name for the PriorAuth resource and used to derive the name of dependent resources.

- Default value: `priorAuth`

### tags

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Tags to be applied to all resources

- Default value: `@{environment=[parameters('environmentName')]; location=[parameters('location')]}`

### openAiApiVersion

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

API Version of the OpenAI API

- Default value: `2024-08-01-preview`

### chatCompletionModels

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

List of completion models to be deployed to the OpenAI account.

### embeddingModel

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

List of embedding models to be deployed to the OpenAI account.

- Default value: `@{name=text-embedding-3-large; version=1; skuName=Standard; capacity=50}`

### embeddingModelDimension

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Embedding model size for the OpenAI Embedding deployment

- Default value: `3072`

### storageBlobContainerName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Storage Blob Container name to land the files for Prior Auth

- Default value: `default`

## Outputs

Name | Type | Description
---- | ---- | -----------
RESOURCE_GROUP_NAME | string | Name of the resource group
CONTAINER_JOB_NAME | string | Name of the container job
AZURE_OPENAI_ENDPOINT | string | Endpoint for Azure OpenAI
AZURE_OPENAI_API_VERSION | string | API version for Azure OpenAI
AZURE_OPENAI_EMBEDDING_DEPLOYMENT | string | Deployment name for Azure OpenAI embedding
AZURE_OPENAI_CHAT_DEPLOYMENT_ID | string | Deployment ID for Azure OpenAI chat
AZURE_OPENAI_CHAT_DEPLOYMENT_01 | string | Deployment name for Azure OpenAI chat model 01
AZURE_OPENAI_EMBEDDING_DIMENSIONS | string | Embedding dimensions for Azure OpenAI
AZURE_SEARCH_SERVICE_NAME | string | Name of the Azure Search service
AZURE_SEARCH_INDEX_NAME | string | Name of the Azure Search index
AZURE_AI_SEARCH_ADMIN_KEY | string | Admin key for Azure AI Search
AZURE_BLOB_CONTAINER_NAME | string | Name of the Azure Blob container
AZURE_STORAGE_ACCOUNT_NAME | string | Name of the Azure Storage account
AZURE_STORAGE_ACCOUNT_KEY | string | Key for the Azure Storage account
AZURE_STORAGE_CONNECTION_STRING | string | Connection string for the Azure Storage account
AZURE_AI_SERVICES_KEY | string | Key for Azure AI services
AZURE_COSMOS_DB_DATABASE_NAME | string | Name of the Azure Cosmos DB database
AZURE_COSMOS_DB_COLLECTION_NAME | string | Name of the Azure Cosmos DB collection
AZURE_COSMOS_CONNECTION_STRING | string | Connection string for Azure Cosmos DB
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT | string | Endpoint for Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_KEY | string | Key for Azure Document Intelligence
APPLICATIONINSIGHTS_CONNECTION_STRING | string | Connection string for Application Insights
AZURE_CONTAINER_REGISTRY_ENDPOINT | string | Endpoint for Azure Container Registry
AZURE_CONTAINER_ENVIRONMENT_ID | string | ID for Azure Container Environment
AZURE_OPENAI_KEY | string | Key for Azure OpenAI
AZURE_AI_SEARCH_SERVICE_ENDPOINT | string | Service endpoint for Azure AI Search

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/main.json"
    },
    "parameters": {
        "environmentName": {
            "value": ""
        },
        "location": {
            "value": ""
        },
        "frontendExists": {
            "value": false
        },
        "backendExists": {
            "value": false
        },
        "priorAuthName": {
            "value": "priorAuth"
        },
        "tags": {
            "value": {
                "environment": "[parameters('environmentName')]",
                "location": "[parameters('location')]"
            }
        },
        "openAiApiVersion": {
            "value": "2024-08-01-preview"
        },
        "chatCompletionModels": {
            "value": [
                {
                    "name": "o1",
                    "version": "2024-12-17",
                    "skuName": "Standard",
                    "capacity": 100
                }
            ]
        },
        "embeddingModel": {
            "value": {
                "name": "text-embedding-3-large",
                "version": "1",
                "skuName": "Standard",
                "capacity": 50
            }
        },
        "embeddingModelDimension": {
            "value": "3072"
        },
        "storageBlobContainerName": {
            "value": "default"
        }
    }
}
```

## Default Values


- **priorAuthName**: priorAuth

- **tags**: @{environment=[parameters('environmentName')]; location=[parameters('location')]}

- **openAiApiVersion**: 2024-08-01-preview

- **chatCompletionModels**: @{name=o1; version=2024-12-17; skuName=Standard; capacity=100}

- **embeddingModel**: @{name=text-embedding-3-large; version=1; skuName=Standard; capacity=50}

- **embeddingModelDimension**: 3072

- **storageBlobContainerName**: default
# resources

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
frontendExists | No       |
backendExists  | No       |
priorAuthName  | No       | Name for the PriorAuth resource and used to derive the name of dependent resources.
tags           | No       | Set of tags to apply to all resources.
cosmosDbCollectionName | No       |
cosmosDbDatabaseName | No       |
openAiApiVersion | No       | API Version of the OpenAI API
chatCompletionModels | No       | List of completion models to be deployed to the OpenAI account.
embeddingModel | No       | List of embedding models to be deployed to the OpenAI account.
embeddingModelDimension | No       | Embedding model size for the OpenAI Embedding deployment
storageBlobContainerName | No       | Storage Blob Container name to land the files for Prior Auth

### frontendExists

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)



- Default value: `False`

### backendExists

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)



- Default value: `False`

### priorAuthName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Name for the PriorAuth resource and used to derive the name of dependent resources.

- Default value: `priorAuth`

### tags

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Set of tags to apply to all resources.

### cosmosDbCollectionName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)



- Default value: `temp`

### cosmosDbDatabaseName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)



- Default value: `priorauthsessions`

### openAiApiVersion

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

API Version of the OpenAI API

- Default value: `2024-08-01-preview`

### chatCompletionModels

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

List of completion models to be deployed to the OpenAI account.

### embeddingModel

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

List of embedding models to be deployed to the OpenAI account.

- Default value: `@{name=text-embedding-ada-002; version=2; skuName=Standard; capacity=16}`

### embeddingModelDimension

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Embedding model size for the OpenAI Embedding deployment

- Default value: `1536`

### storageBlobContainerName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Storage Blob Container name to land the files for Prior Auth

- Default value: `default`

## Outputs

Name | Type | Description
---- | ---- | -----------
AZURE_OPENAI_ENDPOINT | string |
AZURE_OPENAI_API_VERSION | string |
AZURE_OPENAI_EMBEDDING_DEPLOYMENT | string |
AZURE_OPENAI_CHAT_DEPLOYMENT_ID | string |
AZURE_OPENAI_CHAT_DEPLOYMENT_01 | string |
AZURE_OPENAI_EMBEDDING_DIMENSIONS | string |
AZURE_SEARCH_SERVICE_NAME | string |
AZURE_SEARCH_INDEX_NAME | string |
AZURE_AI_SEARCH_ADMIN_KEY | string |
AZURE_AI_SEARCH_SERVICE_ENDPOINT | string |
AZURE_STORAGE_ACCOUNT_KEY | string |
AZURE_BLOB_CONTAINER_NAME | string |
AZURE_STORAGE_ACCOUNT_NAME | string |
AZURE_STORAGE_CONNECTION_STRING | string |
AZURE_AI_SERVICES_KEY | string |
AZURE_COSMOS_DB_DATABASE_NAME | string |
AZURE_COSMOS_DB_COLLECTION_NAME | string |
AZURE_COSMOS_CONNECTION_STRING | string |
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT | string |
AZURE_DOCUMENT_INTELLIGENCE_KEY | string |
APPLICATIONINSIGHTS_CONNECTION_STRING | string |
AZURE_CONTAINER_REGISTRY_ENDPOINT | string |
AZURE_CONTAINER_ENVIRONMENT_ID | string |
AZURE_CONTAINER_ENVIRONMENT_NAME | string |
AZURE_OPENAI_KEY | string |
CONTAINER_JOB_NAME | string |

## Snippets

### Parameter file

```json
{
    "$schema": "https://schema.management.azure.com/schemas/2015-01-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "metadata": {
        "template": "infra/resources.json"
    },
    "parameters": {
        "frontendExists": {
            "value": false
        },
        "backendExists": {
            "value": false
        },
        "priorAuthName": {
            "value": "priorAuth"
        },
        "tags": {
            "value": {}
        },
        "cosmosDbCollectionName": {
            "value": "temp"
        },
        "cosmosDbDatabaseName": {
            "value": "priorauthsessions"
        },
        "openAiApiVersion": {
            "value": "2024-08-01-preview"
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
                "capacity": 16
            }
        },
        "embeddingModelDimension": {
            "value": "1536"
        },
        "storageBlobContainerName": {
            "value": "default"
        }
    }
}
```

## Default Values


- **priorAuthName**: priorAuth

- **tags**:

- **cosmosDbCollectionName**: temp

- **cosmosDbDatabaseName**: priorauthsessions

- **openAiApiVersion**: 2024-08-01-preview

- **chatCompletionModels**: @{name=gpt-4o; version=2024-08-06; skuName=GlobalStandard; capacity=25}

- **embeddingModel**: @{name=text-embedding-ada-002; version=2; skuName=Standard; capacity=16}

- **embeddingModelDimension**: 1536

- **storageBlobContainerName**: default
