---
layout: default
title: "Azure DeveLoper CLI (azd) Deployment"
nav_order: 7
---

# Azure Developer CLI (azd) Deployment Guide

This guide provides step-by-step instructions for deploying the project using Azure Developer CLI (azd).

## Prerequisites

- **Azure Subscription**: Ensure you have an active Azure subscription.
- **Azure Developer CLI**: Install the Azure Developer CLI. Follow the [installation guide](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd).

## Steps to Deploy

### 1. Initialize the Project

Clone the repository and navigate to the project directory.

```bash
git clone https://github.com/your-repo/gbb-ai-hls-factory-prior-auth.git
cd gbb-ai-hls-factory-prior-auth
```


### 2. Provision Infrastructure and Deploy Application

Run the following command to provision the infrastructure and deploy the application.

```bash
azd up
```

On the initial run, the azd cli will walk you through and ask you to provide the required parameters to configure for its deployment.

`azd up` is a combination of `azd provision` (bicep/infra) and `azd deploy` (application image deployment).

This command will:
- Provision the necessary Azure resources defined in [infra/main.bicep](../infra/main.bicep)
- Deploy the application code or 'service(s)' defined in [azure.yaml](../azure.yaml#L6)
    ```yaml
    services:
        streamlit:
            project: app/streamlit
            host: containerapp
            language: python
            docker:
                path: ../../Dockerfile
                context: ../../
                remoteBuild: true
    ```
    To help understand the above configuration, here is the breakdown of the attributes:
    - `services`: This is the top-level key that defines a list of services to be deployed. Each service has its own configuration.
    - `streamlit`: This is the name of the service. In this case, it is named streamlit, which likely refers to a Streamlit application.
    - `project`: Specifies the path to the project directory. Here, streamlit indicates that the Streamlit application is located in the streamlit directory.
    - `host`: Defines the hosting environment for the service. containerapp suggests that the service will be hosted in an Azure Container App.
    - `language`: Indicates the programming language used for the service. python specifies that the application is written in Python.
    - `docker`: Contains Docker-specific configuration for building and deploying the service.
    - `path`: Specifies the path to the Dockerfile. ../../Dockerfile indicates that the Dockerfile is located two directories up from the current directory.
    - `context`: Defines the build context for Docker. Repos means that the build context is set to two directories up from the current directory.
    - `remoteBuild`: A boolean value that indicates whether the build should be performed remotely. true means that the Docker image will be built on a remote server rather than locally.
- Generate the `.env` file for your local development (configured in [`azure.yaml:63`]('../../../azure.yaml#L63))

> ⚠️ **Important**: The Azure Developer CLI (azd) is a powerful and flexible tool that simplifies the process of deploying and managing your applications on Azure. It provides a seamless experience for developers, enabling them to focus on writing code rather than managing infrastructure. To explore the full range of possibilities and configurations that azd offers, refer to the [official azd schema documentation](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/azd-schema).


3. Verify Deployment
After running the azd up command, you can verify the deployment by checking the Azure resources and the application status. Use the following command to list the deployed resources:



### 3. Configure CI/CD Pipeline (OIDC)

This project comes with a basic, azd-based, GitHub Actions example at [.github/workflows/azd_deploy.yml](../.github/workflows/azd_deploy.yml)

> Note: you can also generate your own via `azd pipeline config`

This workflow leverages OpenID Connect (OIDC) for authentication and requires the following GitHub Actions secrets to be set:

 - `AZURE_CLIENT_ID`: The client ID of the Azure AD application.
 - `AZURE_TENANT_ID`: The tenant ID of the Azure AD application.
 - `AZURE_SUBSCRIPTION_ID`: The subscription ID where the resources are located.
 - `AZURE_ENV_NAME`: The name of the Azure environment (i.e 'mycoolenv', 'dev', 'test', 'prod')
 - `AZURE_LOCATION`: The Azure region to deploy the infra resources to.
 - `COSMOS_ADMINISTRATOR_PASSWORD`: The password for the Cosmos DB administrator.

Ensure these secrets are configured in your GitHub repository settings under "Secrets and variables" > "Actions".

> ⚠️ **Important**: If you are not sure how to get these values, be sure to follow the steps outlined in the following document to setup the Entra App Registration:
https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect

####

### 4. Verify Deployment

After the deployment is complete, verify that the application is running by visiting the service endpoints listed in the output of the `azd show` command.

## Troubleshooting

If you encounter any issues during the deployment, refer to the troubleshooting guides for the various services involved in the deployment:
- [Container Apps](https://learn.microsoft.com/azure/container-apps/troubleshooting).
- [Azure AI Search](https://learn.microsoft.com/en-us/azure/search/cognitive-search-common-errors-warnings)
- [Cosmos DB NoSQL](https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/troubleshoot-query-performance)
- [Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/on-your-data-best-practices)
- [Document Intelligence](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/how-to-guides/resolve-errors?view=doc-intel-4.0.0)

## Additional Information

For more information about setting up your `azd` project, visit the official [Azure Developer CLI documentation](https://learn.microsoft.com/azure/developer/azure-developer-cli/make-azd-compatible?pivots=azd-convert).
