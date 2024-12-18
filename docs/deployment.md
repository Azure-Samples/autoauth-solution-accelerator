---
layout: default
title: "Deployment"
nav_order: 5
---

# 🚀 Deployment Guide  

This guide provides a step-by-step walkthrough for deploying the **AutoAuth framework**.

---

## One-Click Deploy AutoAuth Framework

We have encapsulated the necessary steps to deploy the assets into Azure, requiring you to bring:

* Azure Subscription
* OpenAI Access
* Available Quota for Resources
* Working Internet Connection
* *Preferred:* Access enabled to deploy `o1-preview` model on Azure OpenAI

> **Temporary:** Ability to build and push Docker images

Try it now:

### (Optional) Step 0. Enable Authorization for the Application

To utilize the repository with authentication enabled on the deployment, you will need to bring your own identity provider. The template supports Microsoft Entra AD, which you will need to create an App Registration. Follow the app registration guide [here](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app?tabs=certificate)

>[Warning!]
>Creating an application registration does not support personal accounts to access, so you will need to have an account for your Microsoft tenant in order to create the application registration.

Ahead of deployment, you will need the following informaton:

* App Registration Client Secret
* App Registration Client ID
* App Registration Tenant ID

Once you have the above, you are good to proceed to the remaining steps. If you do not have authorization, feel free to deploy the application with `none` when prompted on an identity provider. You may always change this later.

### Step 1. Build the Docker Image

You will need to build the docker image for this repository to work, and you are free to make any changes. You can create the repository on an Azure Container Registry of your choice, similarly:

```bash
docker build -t priorauthdemo.azurecr.io/priorauth-frontend:v1 --file devops/container/Dockerfile .
docker push priorauthdemo.azurecr.io/priorauth-frontend:v1
```

### Step 2. Create the Infrastructure

Included in this repository are our configurations to quickly deploy the infrastructure, you can use `az cli` to create it similarly:

```bash
# May require installing azure-cli-ml extension
# az extension add --name azure-cli-ml
az deployment group create \
    --debug \
    --resource-group "<resourceGroup>" \
    --template-file "devops/infra/main.bicep" \
    --parameters priorAuthName="priorAuth" \
                 tags={} \
                 location="<region>" \
                 cosmosAdministratorPassword="<password>" \
                 acrContainerImage="priorauthdemo.azurecr.io/priorauth-frontend:v2" \
                 acrUsername="<acrUsername>" \
                 acrPassword="<acrPassword>" \
                 aadClientId="<clientId>" \
                 aadClientSecret="<<clientSecret>>" \
                 aadTenantId="<tenant>>" \
                 authProvider="aad"
```

Refer to the scripts in `devops/infra/scripts` folder for build and cleanup capabilities.

Alternatively, one-click deployment is possible:

> *Warning*: Templates below will not populate correctly until this repository is made publicly available.

[![Deploy To Azure](utils/images/deploytoazure.svg?sanitize=true)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Fdevops%2Finfra%2Fmain.json)
[![Visualize](utils/images/visualizebutton.svg?sanitize=true)](http://armviz.io/#/?load=https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Fdevops%2Finfra%2Fmain.json)

If you requested deployment with an identity provider, please go to the next step. All else, go to step 4.

### (Optional) Step 3: Configure App Registration Authentication

In order to complete the login, you must allow your newly deployed container application to be permissable for login from your app registration. This is an additional step to ensure your authentication flow redirects only to permissable web URLs. Read more [here](https://learn.microsoft.com/en-us/azure/app-service/configure-authentication-provider-aad?tabs=workforce-configuration#configure-authentication-settings)

After you configured the authentication to your security specifications, you will want to add a Web URI supporting the new deployment. Navigate to `Authentication` under Manage, and you will want to add a platform configuration. Select `Web`, and when prompted you will want to submit a value of: `<containerAppUrl>/.auth/login/aad/callback`

### Step 4: Access Streamlit UI and Upload Policy Documents

Review your deployment and use your browser to navigate to the URL assigned to your container app. Upload your policy documents, and watch AutoAuth work.

## Azure Native Services

The following services are required for implementation.

| **Service Name**         | **Description**                                                                                   | **Major Components**                                              | **Limits/Defaults**                                                                                                  |
|---------------------------|---------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| **Document Intelligence** | Azure Cognitive Services for AI models related to document processing and intelligence.          | `Microsoft.CognitiveServices/accounts`                            | Default SKU: `S0`. Public network access enabled.                                                                    |
| **OpenAI Service**        | Deploys OpenAI models like `GPT-4o` and `text-embedding-ada-002` for completions and embeddings.  | OpenAI deployments: `GPT-4o` (chat), `o1`. `Text Embedding Ada-002` or `text-embedding-3-*`        | `GPT-4o`: Default capacity: 25. `o1` optional and can test with `GPT-4o`.                                                      |
| **Azure Search**          | Azure AI Search service for indexing and querying data.                                          | `Microsoft.Search/searchServices`                                 | Default SKU: `basic`. Public network access enabled.                                                                  |
| **Multi-Service AI**      | General-purpose Cognitive Services account for accessing multiple AI capabilities.               | `Microsoft.CognitiveServices/accounts`                            | Default SKU: `S0`. Public network access enabled. **Must be multi-service.**                                                                   |
| **Storage Account**       | Azure Storage Account for storing and retrieving blob data.                                      | `Microsoft.Storage/storageAccounts`, Blob containers              | Default SKU: `Standard_LRS`. HTTPS traffic only. Delete retention policy: 7 days. Container created named `pre-auth-policies`.                                   |
| **Application Insights**  | Azure monitoring for application performance and availability.                                   | `Microsoft.Insights/components`                                   | Public network access enabled for ingestion and query.                                                               |
| **Cosmos DB (Mongo)**     | Cosmos DB Mongo cluster for storing NoSQL data with high availability.                           | `Microsoft.DocumentDB/mongoClusters`                              | Default compute tier: M30. Storage: 32 GB. Public network access enabled.                                            |
| **Log Analytics**         | Azure Log Analytics for query-based monitoring.                                                  | `Microsoft.OperationalInsights/workspaces`                        | Retention: 30 days.                                                                                                   |
| **Container Apps**        | Azure Container Apps for running microservices and managing workloads.                           | `Microsoft.App/containerApps`, `Microsoft.App/jobs`               | Workload profile: `Consumption`. CPU: 2.0 cores. Memory: 4 GiB per container. Ingress port: 8501.                    |

