> **NOTICE**: This page has been archived. Please refer to [**azd_deployment.md**](./azd_deployment.md) for the latest deployment instructions.

```
---
layout: default
title: "Deployment"
nav_order: 6
---

# 🚀 Deployment Guide

Quickly deploy the AutoAuth framework into your Azure environment using one-click templates and infrastructure as code.

## Prerequisites

- **Azure Subscription** with permission to create resources
- **OpenAI Access** enabled on your Azure subscription
- **Resource Quotas** available for Cognitive Search, Storage, and OpenAI

## One-Click Deployment

Use the provided button to deploy all necessary infrastructure:

[![Deploy To Azure](utils/images/deploytoazure.svg?sanitize=true)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Finfra%2Fmain.json)
[![Visualize](utils/images/visualizebutton.svg?sanitize=true)](http://armviz.io/#/?load=https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Finfra%2Fmain.json)

## Steps

1. **Click Deploy to Azure**: Follow prompts in the Azure Portal.
2. **Configure Parameters**: Set desired resource names and locations.
3. **Review & Create**: Validate the template and create resources.

Once complete, you’ll have a fully provisioned environment, ready for indexing policies, running the pipeline, and exploring the application UI.

## Authentication & Customization

- If using identity providers, configure Microsoft Entra ID as outlined in the [Customization](#customization-and-advanced-configurations) section below. Set `authProvider` to `aad` to protect the container application deployment with your app registration.
- Adjust environment variables and prompts as needed to tailor the solution to your workflow.

## Entra Authentication Module: Optional Steps for Configuring Identity

Configuring Entra for your deployment is a two-step process, which requires a pre-step as well as a post-step. These steps can be done with or without the template and can be done at anytime.

### Step 1: Create an App Registration (Pre-Deployment)

To deploy the application with an identity provider, such as **Microsoft Entra ID**, you need to set up an App Registration. This involves creating a registered application in Microsoft Entra (formerly Azure Active Directory). Follow these steps:

1. **Register the Application**:
   - Follow the [App Registration Guide](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app?tabs=certificate) to create an app registration in Microsoft Entra ID.

2. **Collect Required Information**:
   - Once the app is registered, obtain the following details:
     - **Client ID** (App Registration ID)
     - **Client Secret** (Generated during app registration)
     - **Tenant ID**

3. **Deploy Without Authentication** *(Optional)*:
   - If you want to deploy without an identity provider initially, set `authProvider="none"` during the deployment process. You can enable authentication later by updating the parameters.

> [!WARNING]
> **Important**: Personal Microsoft accounts are not supported for creating app registrations. Ensure you are using a Microsoft tenant account with sufficient permissions.

---

### Step 2: Configure Authentication Redirect URI for the Application (Post-Deployment)

To enable the login flow for your deployed container application, you must configure the App Registration to allow redirects from your deployed app's URL.

1. **Navigate to the App Registration**:
   - Open the **Azure Portal** and go to the **App Registration** created earlier.

2. **Update Authentication Settings**:
   - Under **Manage**, select **Authentication**.
   - Add a **Platform Configuration**:
     - Choose **Web**.
     - Add the redirect URI for your container app:
       `<containerAppUrl>/.auth/login/aad/callback`

3. **Save Changes**:
   - Review and save the configuration to ensure proper authentication flow.

> [!TIP]
> **Note**: The `<containerAppUrl>` is the URL of your deployed container application. Replace it with the actual URL once your deployment is complete.

4. **Test Authentication**:
   - Navigate to your container application and verify that you can log in using the configured App Registration.

## Infrastructure Parameters

The table below explains the parameters in the ARM template, including their descriptions, default values, and whether they are required.

> [!WARNING]
> Due to limited model availability, ensure that the location parameter is set to a supported region for the embedding model you wish to use. For text-embedding-3-large, supported regions include: australiaeast, canadaeast, eastus, eastus2, francecentral, japaneast, norwayeast, polandcentral, southindia, swedencentral, switzerlandnorth, uksouth, westus3

| Parameter Name            | Type         | Description                                                                                              | Default Value                                | Required |
|---------------------------|--------------|----------------------------------------------------------------------------------------------------------|--------------------------------------------|----------|
| `priorAuthName`           | `string`     | Name for the PriorAuth resource and used to derive the name of dependent resources.                     | `priorAuth`                                | Yes      |
| `tags`                    | `object`     | Set of tags to apply to all resources.                                                                   | `{}`                                       | No       |
| `acrContainerImage`       | `securestring`| ACR container image URL.                                                                                 | None                                       | Yes      |
| `acrUsername`             | `securestring`| Admin user for the ACR registry of the container image.                                                  | None                                       | Yes      |
| `acrPassword`             | `securestring`| Admin password for the ACR registry of the container image.                                              | None                                       | Yes      |
| `cosmosAdministratorPassword`| `securestring`| Admin password for the Cosmos DB cluster.                                                                | None                                       | Yes      |
| `location`                | `string`     | The location into which the resources should be deployed.                                                | `[resourceGroup().location]`               | Yes      |
| `openAiApiVersion`        | `string`     | API Version of the OpenAI API.                                                                           | `2024-08-01-preview`                       | Yes      |
| `chatCompletionModels`    | `array`      | List of chat completion models to deploy in OpenAI.                                                      | See template for details                   | No       |
| `embeddingModel`          | `object`     | Embedding model configuration for OpenAI.                                                                | See template for details                   | No       |
| `embeddingModelDimension` | `string`     | Embedding model size for the OpenAI embedding deployment.                                                | `1536`                                     | No       |
| `storageBlobContainerName`| `string`     | Storage Blob Container name for Prior Auth.                                                              | `default`                                  | No       |
| `appRegistrationName`     | `string`     | App Registration Name.                                                                                   | `""`                                       | No       |
| `aadClientId`             | `string`     | AAD Client ID (App Registration ID) for the Container App.                                               | `""`                                       | Conditional (if `authProvider` = `aad`) |
| `aadClientSecret`         | `securestring`| AAD Client Secret for the Container App.                                                                 | `""`                                       | Conditional (if `authProvider` = `aad`) |
| `aadTenantId`             | `string`     | AAD Tenant ID for the Container App.                                                                     | `""`                                       | Conditional (if `authProvider` = `aad`) |
| `authProvider`            | `string`     | Authentication provider to use. Allowed values: `aad`, `none`.                                           | `none`                                     | No       |

#### Notes on Parameter Configuration

1. **Required Parameters**: Parameters like `priorAuthName`, `acrContainerImage`, and `cosmosAdministratorPassword` must be configured before deployment.
2. **Conditional Parameters**: If the `authProvider` is set to `aad`, you must provide `aadClientId`, `aadClientSecret`, and `aadTenantId`. For unauthenticated deployment, set `authProvider` to `none`.
3. **Model Configuration**: Update `chatCompletionModels` and `embeddingModel` parameters to include your desired OpenAI models. Ensure sufficient capacity is allocated.

> [!TIP]
> By default, the application launches with GPT-4o capacity. The system performance and results perform much better with the `o1` model, which you can configure by editing the `chatCompletionModels` deployment parameter and the `AZURE_OPENAI_CHAT_DEPLOYMENT_01` parameter of the compute deployment to use the same `o1` deployment.

##### Example Configuration

```json
{
  "priorAuthName": "myPriorAuth",
  "tags": {
    "environment": "production",
    "owner": "team-name"
  },
  "acrContainerImage": "myregistry.azurecr.io/myapp:latest",
  "acrUsername": "myACRUser",
  "acrPassword": "myACRPassword",
  "cosmosAdministratorPassword": "myCosmosPassword",
  "location": "eastus",
  "openAiApiVersion": "2024-08-01-preview",
  "authProvider": "aad",
  "aadClientId": "myAADClientId",
  "aadClientSecret": "myAADClientSecret",
  "aadTenantId": "myAADTenantId"
}
```

## Azure Native Services

| **Service Name**          | **Description**                                                                                   | **Major Components**                     | **Limits/Defaults**                                                                                       |
|----------------------------|---------------------------------------------------------------------------------------------------|------------------------------------------|----------------------------------------------------------------------------------------------------------|
| **Document Intelligence**  | Azure Cognitive Services for AI models related to document processing and intelligence.          | `Microsoft.CognitiveServices/accounts`   | Default SKU: `S0`. Public network access enabled.                                                       |
| **OpenAI Service**         | Deploys OpenAI models like `GPT-4o` and `text-embedding-ada-002`.                                | `Microsoft.CognitiveServices/accounts`   | Default capacity and SKUs vary by region.                                                               |
| **Azure Search**           | Azure AI Search service for indexing and querying data.                                          | `Microsoft.Search/searchServices`        | Default SKU: `basic`. Public network access enabled.                                                    |
| **Multi-Service AI**       | General-purpose Cognitive Services account.                                                      | `Microsoft.CognitiveServices/accounts`   | Default SKU: `S0`. Public network access enabled.                                                       |
| **Storage Account**        | Azure Storage Account for storing blob data.                                                     | `Microsoft.Storage/storageAccounts`      | Default SKU: `Standard_LRS`. HTTPS only. Container: `pre-auth-policies`.                                 |
| **Application Insights**   | Azure monitoring for app performance and availability.                                           | `Microsoft.Insights/components`          | Public network access enabled.                                                                          |
| **Cosmos DB (Mongo)**      | Cosmos DB Mongo cluster for storing NoSQL data.                                                  | `Microsoft.DocumentDB/mongoClusters`     | Default compute tier: M30, Storage: 32 GB. Public network access enabled.                               |
| **Log Analytics**          | Azure Log Analytics for query-based monitoring.                                                  | `Microsoft.OperationalInsights/workspaces`| Retention: 30 days.                                                                                      |
| **Container Apps**         | Azure Container Apps for running microservices.                                                  | `Microsoft.App/containerApps`            | CPU: 2.0 cores, Memory: 4 GiB per container. Ingress port: 8501.                                         |

## Getting Started Locally with AutoAuth Framework

### Step 1: Create and Activate the Conda Environment

#### For Windows Users:

```bash
conda env create -f environment.yaml
conda activate pa-ai-env
```

#### For Linux/WSL Users:

```bash
make create_conda_env
```

### Step 2: Configure Environment Variables

1. Copy `.env.sample` to `.env`.
2. Populate the `.env` with your keys and service names.

### Step 3: Index Policies

Run `01-indexing-policies.ipynb` to index policies into Azure Search.

### Step 4: Run the Application

```bash
streamlit run app/streamlit/Home.py
```

*(Ensure `PYTHONPATH` includes the repo root if needed.)*

### Step 5: Data Sources

- Data and test cases are in `utils/data/`.
```
