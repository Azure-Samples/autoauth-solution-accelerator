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
enableEasyAuth | No       | Flag to indicate if EasyAuth should be enabled for the Container Apps (Defaults to true)
disableIngress | No       | Flag to indicate if the Container App should be deployed with ingress disabled
environmentName | Yes      | Name of the environment that can be used as part of naming resource convention
location       | Yes      | Primary location for all resources. Not all regions are supported due to OpenAI limitations
frontendExists | No       | Flag to indicate if Frontend app image exists. This is managed by AZD
backendExists  | No       | Flag to indicate if Backend app image exists. This is managed by AZD
priorAuthName  | No       | Name for the PriorAuth resource and used to derive the name of dependent resources.
tags           | No       | Tags to be applied to all resources
openAiApiVersion | No       | API Version of the OpenAI API
reasoningModel | No       | Reasoning model object to be deployed to the OpenAI account. (i.e o1, o1-preview, o3-mini)
chatModel      | No       | Chat model object to be deployed to the OpenAI account. (i.e gpt-4o, gpt-4o-turbo, gpt-4o-turbo-16k, gpt-4o-turbo-32k)
embeddingModel | No       | Embedding model to be deployed to the OpenAI account.
GIT_HASH       | No       | Unique hash of the git commit that is being deployed. This is used to tag resources and support llm evaluation automation.
embeddingModelDimension | No       | Embedding model size for the OpenAI Embedding deployment
storageBlobContainerName | No       | Storage Blob Container name to land the files for Prior Auth

### enableEasyAuth

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Flag to indicate if EasyAuth should be enabled for the Container Apps (Defaults to true)

- Default value: `True`

### disableIngress

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Flag to indicate if the Container App should be deployed with ingress disabled

- Default value: `False`

### environmentName

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Name of the environment that can be used as part of naming resource convention

### location

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Primary location for all resources. Not all regions are supported due to OpenAI limitations

- Allowed values: `eastus2`, `swedencentral`

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

- Default value: `@{environment=[parameters('environmentName')]; location=[parameters('location')]; commit=[parameters('GIT_HASH')]}`

### openAiApiVersion

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

API Version of the OpenAI API

- Default value: `2025-01-01-preview`

### reasoningModel

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Reasoning model object to be deployed to the OpenAI account. (i.e o1, o1-preview, o3-mini)

- Default value: `@{name=o1; version=2025-01-01-preview; skuName=GlobalStandard; capacity=100}`

### chatModel

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Chat model object to be deployed to the OpenAI account. (i.e gpt-4o, gpt-4o-turbo, gpt-4o-turbo-16k, gpt-4o-turbo-32k)

- Default value: `@{name=gpt-4o; version=2024-08-06; skuName=GlobalStandard; capacity=100}`

### embeddingModel

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Embedding model to be deployed to the OpenAI account.

- Default value: `@{name=text-embedding-3-large; version=1; skuName=Standard; capacity=50}`

### GIT_HASH

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Unique hash of the git commit that is being deployed. This is used to tag resources and support llm evaluation automation.

- Default value: `azd-deploy-1741105197`

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
AZURE_RESOURCE_GROUP | string | Name of the resource group
CONTAINER_JOB_NAME | string | Name of the container job
AZURE_OPENAI_ENDPOINT | string | Endpoint for Azure OpenAI
AZURE_OPENAI_API_VERSION | string | API version for Azure OpenAI
AZURE_OPENAI_EMBEDDING_DEPLOYMENT | string | Deployment name for Azure OpenAI embedding
AZURE_OPENAI_CHAT_DEPLOYMENT_ID | string | Deployment ID for Azure OpenAI chat
AZURE_OPENAI_CHAT_DEPLOYMENT_01 | string | Deployment name for Azure OpenAI chat model 01
AZURE_OPENAI_API_VERSION_01 | string | Deployment openai version for chat model 01
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
AZURE_AI_FOUNDRY_CONNECTION_STRING | string | AI Foundry connection string to connect to AI Foundry

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
        "enableEasyAuth": {
            "value": true
        },
        "disableIngress": {
            "value": false
        },
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
                "location": "[parameters('location')]",
                "commit": "[parameters('GIT_HASH')]"
            }
        },
        "openAiApiVersion": {
            "value": "2025-01-01-preview"
        },
        "reasoningModel": {
            "value": {
                "name": "o1",
                "version": "2025-01-01-preview",
                "skuName": "GlobalStandard",
                "capacity": 100
            }
        },
        "chatModel": {
            "value": {
                "name": "gpt-4o",
                "version": "2024-08-06",
                "skuName": "GlobalStandard",
                "capacity": 100
            }
        },
        "embeddingModel": {
            "value": {
                "name": "text-embedding-3-large",
                "version": "1",
                "skuName": "Standard",
                "capacity": 50
            }
        },
        "GIT_HASH": {
            "value": "azd-deploy-1741105197"
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


- **enableEasyAuth**: True

- **priorAuthName**: priorAuth

- **tags**: @{environment=[parameters('environmentName')]; location=[parameters('location')]; commit=[parameters('GIT_HASH')]}

- **openAiApiVersion**: 2025-01-01-preview

- **reasoningModel**: @{name=o1; version=2025-01-01-preview; skuName=GlobalStandard; capacity=100}

- **chatModel**: @{name=gpt-4o; version=2024-08-06; skuName=GlobalStandard; capacity=100}

- **embeddingModel**: @{name=text-embedding-3-large; version=1; skuName=Standard; capacity=50}

- **GIT_HASH**: azd-deploy-1741105197

- **embeddingModelDimension**: 3072

- **storageBlobContainerName**: default
# resources

## Parameters

Parameter name | Required | Description
-------------- | -------- | -----------
frontendExists | No       |
backendExists  | No       |
enableEasyAuth | Yes      | Flag to indicate if EasyAuth should be enabled for the Container Apps (Defaults to true)
disableIngress | Yes      | Flag to indicate if the Container App should be deployed with ingress disabled
priorAuthName  | No       | Name for the PriorAuth resource and used to derive the name of dependent resources.
tags           | No       | Set of tags to apply to all resources.
openaiApiVersion | Yes      | API Version of the OpenAI API
cosmosDbCollectionName | No       |
cosmosDbDatabaseName | No       |
reasoningModel | Yes      |
chatModel      | Yes      |
embeddingModel | Yes      |
gitHash        | No       |
embeddingModelDimension | Yes      | Embedding model size for the OpenAI Embedding deployment
storageBlobContainerName | No       | Storage Blob Container name to land the files for Prior Auth

### frontendExists

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)



- Default value: `False`

### backendExists

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)



- Default value: `False`

### enableEasyAuth

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Flag to indicate if EasyAuth should be enabled for the Container Apps (Defaults to true)

### disableIngress

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Flag to indicate if the Container App should be deployed with ingress disabled

### priorAuthName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Name for the PriorAuth resource and used to derive the name of dependent resources.

- Default value: `priorAuth`

### tags

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)

Set of tags to apply to all resources.

### openaiApiVersion

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

API Version of the OpenAI API

### cosmosDbCollectionName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)



- Default value: `temp`

### cosmosDbDatabaseName

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)



- Default value: `priorauthsessions`

### reasoningModel

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)



### chatModel

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)



### embeddingModel

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)



### gitHash

![Parameter Setting](https://img.shields.io/badge/parameter-optional-green?style=flat-square)



### embeddingModelDimension

![Parameter Setting](https://img.shields.io/badge/parameter-required-orange?style=flat-square)

Embedding model size for the OpenAI Embedding deployment

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
AZURE_AI_FOUNDRY_CONNECTION_STRING | string |
CONTAINER_JOB_NAME | string |
FRONTEND_CONTAINER_URL | string |
FRONTEND_CONTAINER_NAME | string |
APP_IDENTITY_CLIENT_ID | string |
APP_IDENTITY_PRINCIPAL_ID | string |

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
        "enableEasyAuth": {
            "value": null
        },
        "disableIngress": {
            "value": null
        },
        "priorAuthName": {
            "value": "priorAuth"
        },
        "tags": {
            "value": {}
        },
        "openaiApiVersion": {
            "value": ""
        },
        "cosmosDbCollectionName": {
            "value": "temp"
        },
        "cosmosDbDatabaseName": {
            "value": "priorauthsessions"
        },
        "reasoningModel": {
            "value": {}
        },
        "chatModel": {
            "value": {}
        },
        "embeddingModel": {
            "value": {}
        },
        "gitHash": {
            "value": ""
        },
        "embeddingModelDimension": {
            "value": ""
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

- **storageBlobContainerName**: default
