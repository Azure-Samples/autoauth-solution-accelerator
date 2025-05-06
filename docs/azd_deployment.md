---
layout: default
title: "End-to-End Deployment using Azure Developer CLI"
nav_order: 7
---

# End-to-End Deployment using Azure Developer CLI

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Steps](#deployment-steps)
3. [Run the App Locally](#run-the-app-locally)
4. [Customizing or Configuring AZD Deployments](#customizing-or-configuring-azd-deployments)
5. [CI/CD with Azure Developer CLI (azd)](#cicd-with-azure-developer-cli-azd)
6. [Required Secrets for Federated Workload Identities](#required-secrets-for-federated-workload-identities)
7. [Verify Deployment](#verify-deployment)
8. [Troubleshooting](#troubleshooting)

This guide covers how to deploy the project end-to-end with Azure Developer CLI (azd).

## Prerequisites

1. **Azure Role Permissions (Subscription Scope)**
    - You need `Contributor` to provision resources.
    - You need `User Access Administrator` to assign roles to managed identities.

1. **Enable EasyAuth Permissions**
      - To use [EasyAuth](https://learn.microsoft.com/en-us/azure/container-apps/authentication), ensure you have the following permissions:
        - **Create Service Principals**: Required to generate the necessary identities for EasyAuth.
        - **Authorize API Permissions on Entra**: Required to grant API permissions for the service principal to access resources securely.
      - If you lack these permissions, contact your Azure administrator to grant them or perform these actions on your behalf.

1. **Install Docker**
    - Docker is required to build and publish container images to Azure Container Registry (ACR). Follow the steps below to install Docker:
      - **Windows/Mac**: Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
      - **Linux**: Follow the [official Docker installation guide](https://docs.docker.com/engine/install/).
    - After installation, verify Docker is running by executing:
      ```bash
      docker --version
      ```
    - Ensure you have sufficient permissions to run Docker commands. On Linux, you may need to add your user to the `docker` group:
      ```bash
      sudo usermod -aG docker $USER
      ```
      Log out and back in for the changes to take effect.

1. **Install Azure Developer CLI**
    - Follow the [installation guide](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd).

1. **Check Model Availability by Region**
    - **Check Azure OpenAI Model Availability**: This solution uses the following models by default:
      - Reasoning model: `o1`
      - Chat completions model: `gpt-4o`
      - Embeddings model: `text-embedding-3-large`

      Before deployment, verify these models are available in your target region using the [Azure OpenAI models documentation](https://learn.microsoft.com/azure/ai-services/openai/concepts/models?tabs=global-standard%2Cstandard-chat-completions#models-by-deployment-type). If any model isn't available in your region, update the corresponding parameter in `infra/main.parameters.json` with an alternative model.

1. **Initialize Environment**
    - Run `azd init` to prepare your environment.
        -  Be sure to select "Use code in the current directory"




## Deployment Steps

1. **Adjust Infra Config [Optional]**
  - You can use the variables provided in the defaults in [infra/main.parameters.json](https://github.com/Azure-Samples/autoauth-solution-accelerator/blob/main/infra/main.parameters.json), or you can choose to provide your own desired values.

    <details>
      <summary><strong style="color: blue; cursor: pointer;">Main Deployment Parameters (main.bicep)</strong></summary>
      <table>
        <thead>
          <tr>
            <th>Parameter name</th>
            <th>Required</th>
            <th>Description</th>
            <th>Example</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>enableEasyAuth</td>
            <td>No</td>
            <td>Flag to indicate if EasyAuth should be enabled for the Container Apps (Defaults to true)</td>
            <td><code>true</code></td>
          </tr>
          <tr>
            <td>disableIngress</td>
            <td>No</td>
            <td>Flag to indicate if the Container App should be deployed with ingress disabled</td>
            <td><code>false</code></td>
          </tr>
          <tr>
            <td>environmentName</td>
            <td>Yes</td>
            <td>Name of the environment that can be used as part of naming resource convention</td>
            <td><code>dev</code></td>
          </tr>
          <tr>
            <td>location</td>
            <td>Yes</td>
            <td>Primary location for all resources. Not all regions are supported due to OpenAI limitations</td>
            <td><code>eastus</code></td>
          </tr>
          <tr>
            <td>frontendExists</td>
            <td>No</td>
            <td>Flag to indicate if Frontend app image exists. This is managed by AZD</td>
            <td><code>false</code></td>
          </tr>
          <tr>
            <td>backendExists</td>
            <td>No</td>
            <td>Flag to indicate if Backend app image exists. This is managed by AZD</td>
            <td><code>false</code></td>
          </tr>
          <tr>
            <td>priorAuthName</td>
            <td>No</td>
            <td>Name for the PriorAuth resource and used to derive the name of dependent resources</td>
            <td><code>priorAuth</code></td>
          </tr>
          <tr>
            <td>tags</td>
            <td>No</td>
            <td>Tags to be applied to all resources</td>
            <td><code>{ environment: 'dev', location: 'eastus' }</code></td>
          </tr>
          <tr>
            <td>openAiApiVersion</td>
            <td>No</td>
            <td>API Version of the OpenAI API</td>
            <td><code>2025-01-01-preview</code></td>
          </tr>
          <tr>
            <td>reasoningModel</td>
            <td>No</td>
            <td>Reasoning model object to be deployed to the OpenAI account (i.e o1, o1-preview, o3-mini)</td>
            <td><code>{ name: 'o1', version: '2025-01-01-preview', skuName: 'GlobalStandard', capacity: 100 }</code></td>
          </tr>
          <tr>
            <td>chatModel</td>
            <td>No</td>
            <td>Chat model object to be deployed to the OpenAI account (i.e gpt-4o, gpt-4o-turbo, gpt-4o-turbo-16k, gpt-4o-turbo-32k)</td>
            <td><code>{ name: 'gpt-4o', version: '2024-08-06', skuName: 'GlobalStandard', capacity: 100 }</code></td>
          </tr>
          <tr>
            <td>embeddingModel</td>
            <td>No</td>
            <td>Embedding model to be deployed to the OpenAI account</td>
            <td><code>{ name: 'text-embedding-3-large', version: '1', skuName: 'Standard', capacity: 50 }</code></td>
          </tr>
          <tr>
            <td>GIT_HASH</td>
            <td>No</td>
            <td>Unique hash of the git commit that is being deployed. This is used to tag resources and support llm evaluation automation</td>
            <td><code>azd-deploy-1741105197</code></td>
          </tr>
          <tr>
            <td>embeddingModelDimension</td>
            <td>No</td>
            <td>Embedding model size for the OpenAI Embedding deployment</td>
            <td><code>3072</code></td>
          </tr>
          <tr>
            <td>storageBlobContainerName</td>
            <td>No</td>
            <td>Storage Blob Container name to land the files for Prior Auth</td>
            <td><code>default</code></td>
          </tr>
        </tbody>
      </table>
    </details>

    > **Note:** If you don't have access to the `o1` model yet, try using the `gpt-4o` configuration for the `reasoningModel`
     ```json
        "reasoningModel": {
          "value": [
            {
              "name": "gpt-4o",
              "version": "2024-08-06",
              "skuName": "Standard",
              "capacity": 100
            }
          ]
        }
      ```
1. **Guided End-to-End Deployment to Azure**
    To get up and running right away:
    ```bash
    azd up
    ```

      **Understand `azd` command structure:**
      - `azd provision`: Only provisions infrastructure resources defined in the `/infra` directory
      - `azd deploy`: Only deploys applications to already-provisioned infrastructure as defined in `azure.yaml`
      - `azd up`: Combines both steps (provision + deploy) in a single command
        - If you want to deploy only a specific service, use `azd deploy <service>` (e.g., `azd deploy frontend`).
        - This provisions defined resources in [infra/main.bicep](https://github.com/Azure-Samples/autoauth-solution-accelerator/blob/main/infra/main.bicep) and deploys services defined in [azure.yaml](https://github.com/Azure-Samples/autoauth-solution-accelerator/blob/main/azure.yaml#L6), generating a `.env` file for local development.

1. **During Deployment**
    - AZD will guide you through certain deployment flag parameters:

      | Parameter Name | Description |
      |----------------|-------------|
      | `ENABLE_EASY_AUTH` | Given your deployment identity has the permissions to create service principals, enabling this flag will enable Entra sign-ons on your deployed applications so only users in your tenant may access. |
      | `DISABLE_INGRESS` | This flag will disable the network ingress into your container app. Enabling this flag will make your container application unrouteable. |
      | `RUN_EVALS` | This flag will run the pytest large language model evaluations after the |

1. **Post Deployment Model Evaluation**
    The solution includes functionality to evaluate AI model performance (see [postdeploy.sh](https://github.com/Azure-Samples/autoauth-solution-accelerator/blob/main/utils/azd/hooks/postdeploy.sh) for more details and customization):
    ```bash
    # Enable model evaluations
    export RUN_EVALS=true
    azd deploy

    # Alternatively, you can run the script directly once you had a successful deployment.
    # From your autoauth project root directory..
    export RUN_EVALS=true
    ./utils/azd/hooks/postdeploy.sh
    ```

1. **Verify Deployment**
    - Run `azd show` to confirm resources and endpoints.
    - Run `azd monitor show` to open the application dashboard

## Run the App Locally

To run and debug this project locally, you need to set up a Python environment with the required dependencies. You can choose either Conda or virtualenv for environment management.

### Option 1: Using Conda

1. **[Optional] Install Conda**
    - If you don't have Conda installed, download and install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/download/)

2. **Create and activate the environment**
    ```bash
    # Create Python environment from the YAML file
    conda env create -f environment.yaml

    # Activate the environment
    conda activate pa-ai-env
    ```

### Option 2: Using Python virtualenv

1. **Create a virtual environment**
    ```bash
    # Create a new virtual environment (ensure you're using Python 3.10+)
    python -m venv .venv

    # Activate the environment
    source .venv/bin/activate
    ```

2. **Install requirements**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

#### Method 1: Using VS Code Debugger

1. **Configure environment in VS Code**
    - Ensure VS Code is using your conda environment or virtualenv
    - In VS Code, press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
    - Type "Python: Select Interpreter" and select your environment

1. **Run with debugger**
    - Open the Streamlit frontend file in the editor
    - Go to the "Run and Debug" view in the sidebar (or press `Ctrl+Shift+D`)
    - Select "Python: Streamlit" from the dropdown menu (or create this configuration if it doesn't exist)
    - Click the green play button or press `F5` to start debugging

#### Method 2: Running Directly with Python

You can also run the Streamlit frontend directly using Python:

```bash
# Make sure your environment is activated, then run:
python app/frontend/streamlit/Home.py
```

#### Accessing the Application

- Once running, the Streamlit app should automatically open in your default web browser
- If not, you can access it at http://localhost:8501


## Customizing or Configuring AZD Deployments

- **Workflow Definition**
  - [azure.yaml](./azure.yaml): Controls azd behavior, hooks, infrastructure definition, and app deployment.
- **Pre/Post Scripts**
  - [utils/azd/hooks](./utils/azd/hooks/): Holds scripts (e.g., `postprovision`) that update `.env`.
- **Infrastructure**
  - [infra/main.bicep](infra/main.bicep): Main entry point for infrastructure provisioning.
  - [infra/resources.bicep](infra/resources.bicep): Core deployment resources.
  - [infra/main.parameters.json](infra/main.parameters.json): Default deployment values, overrideable by ENV vars.
  - Use `azd provision` to only provision infrastructure.
- **Application Definitions**
  - Apps map to provisioned resources via tags, referencing service names in [azure.yaml](./azure.yaml).
  - For testing only the application layer, use `azd deploy <service>`.

### CI/CD with Azure Developer CLI (azd)

You can automate deployment with azd-generated pipelines.

1. **Create a Pipeline**
    - Run `azd pipeline config` to generate pipeline files for GitHub Actions.
2. **Use Existing Pipelines**
    - Reference [.github/workflows/azd_deploy.yml](https://github.com/Azure-Samples/autoauth-solution-accelerator/blob/main/.github/workflows/azd_deploy.yml) for GitHub Actions.

### Required Secrets for Federated Workload Identities

Refer to [Azure GitHub OIDC docs](https://learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect) for creating these values.

Add these secrets and variables to your GitHub repository under "Secrets and variables" → "Actions":

#### Secrets
- `AZURE_CLIENT_ID`: Client ID of your Service Principal/Managed Identity (e.g., `00000000-0000-0000-0000-000000000000`)
- `AZURE_TENANT_ID`: Your Azure Tenant ID (e.g., `00000000-0000-0000-0000-000000000000`)
- `AZURE_SUBSCRIPTION_ID`: Your Azure Subscription ID (e.g., `00000000-0000-0000-0000-000000000000`)

#### Variables
- `AZURE_ENV_NAME`: Specifies the Azure Developer CLI environment name (e.g `dev`)
- `AZURE_LOCATION`: Specifies the Azure region to deploy to (e.g `eastus2`)

```yaml
name: Azure Developer CLI Deploy

on:
  push:
     branches:
        - main

jobs:
  build:
     runs-on: ubuntu-latest
     env:
        AZURE_CLIENT_ID: "${{ secrets.AZURE_CLIENT_ID }}"
        AZURE_TENANT_ID: "${{ secrets.AZURE_TENANT_ID }}"
        AZURE_SUBSCRIPTION_ID: "${{ secrets.AZURE_SUBSCRIPTION_ID }}"
        AZURE_ENV_NAME: "${{ vars.AZURE_ENV_NAME }}"
        AZURE_LOCATION: "${{ vars.AZURE_LOCATION }}"
     steps:
        - name: Checkout
          uses: actions/checkout@v4
        - name: Install azd
          uses: Azure/setup-azd@v1.0.0
        - name: Log in with Azure (Federated Credentials)
          run: |
             azd auth login `
                --client-id "$Env:AZURE_CLIENT_ID" `
                --federated-credential-provider "github" `
                --tenant-id "$Env:AZURE_TENANT_ID"
          shell: pwsh
        - name: Provision Infrastructure
          id: provision
          run: azd up --no-prompt
          env:
             AZD_INITIAL_ENVIRONMENT_CONFIG: "${{ secrets.AZD_INITIAL_ENVIRONMENT_CONFIG }}"
```

### Verify Deployment

After deployment, visit the service endpoints returned by `azd show`.

## Troubleshooting


1. **Authentication Errors**
    - Ensure that your Azure CLI is logged in with the correct account.
      - run `az account show` to check your local azure credentials
      - run `az login` or `azd auth login` to refresh your credentials
    - Verify that the service principal or managed identity has the necessary permissions.

1. **OpenAI Model Unavailable in your Region**
    - Reference [Azure OpenAI models documentation](https://learn.microsoft.com/azure/ai-services/openai/concepts/models?tabs=global-standard%2Cstandard-chat-completions#models-by-deployment-type) to ensure your current region has support for your desired Azure OpenAI models.


1. **Resource Provisioning Failures**
    - Check the Azure portal for any resource-specific error messages under the deployments tab.
    - Ensure that your subscription has sufficient quota and that the region supports the requested resources.

        ![Azure Portal Resource Group Deployment](./images/azp_help_deployments.png)

1. **Configuration Errors**
    1. **Check the AI Search Service**
        - Verify if the index has been properly created by checking the `Indexes`, `Indexer`, and `Data Source` tabs.
        - Ensure the managed identity used by the AI Search service has `Storage Blob Data Reader` or higher level of access to the storage account.
        - If no documents are populated, and there aren't any `Indexes`, `Indexers`, or `Data Sources` populated, then the `Container App Job` may have failed.
            - To retry or debug the `Container App Job`:
            ![Azure Portal Container App Job Retry](./images/azp_help_containerjoblogs_1.png)


1. **Pipeline Failures**
    - Check the pipeline logs for detailed error messages.
    - Ensure that all required secrets and variables are correctly configured in your GitHub repository.

1. **Application Errors**
    - View the detailed logs of the Container App:
        - First, navigate to either the `Logs` or `Log Stream`
            ![Azure Portal Container App Logs Navigation1](./images/azp_help_containerlogs_1.png)

            - `Log Stream` will stream the live data from your container, however when there are issues with the container itself, you may not be able to see the `console` log due to the container being in a failed state.

            - `Logs` will display all of your `system` and `console` logs, but there is a minor delay in the data.

                ![Azure Portal Getting Logs](images/azp_help_containerlogs_2.png)



For more detailed troubleshooting steps, refer to the specific service documentation linked in the Troubleshooting section.


If you encounter issues:
- [Container Apps](https://learn.microsoft.com/azure/container-apps/troubleshooting)
- [Azure AI Search](https://learn.microsoft.com/azure/search/cognitive-search-common-errors-warnings)
- [Cosmos DB NoSQL](https://learn.microsoft.com/azure/cosmos-db/nosql/troubleshoot-query-performance)
- [Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/how-to/on-your-data-best-practices)
- [Document Intelligence](https://learn.microsoft.com/azure/ai-services/document-intelligence/how-to-guides/resolve-errors?view=doc-intel-4.0.0)

For more on azd projects, see [Azure Developer CLI docs](https://learn.microsoft.com/azure/developer/azure-developer-cli/make-azd-compatible?pivots=azd-convert).
