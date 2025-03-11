#!/bin/bash
# set -x

echo "Checking if Container App Job exists and has successful executions..."
job_name=$(azd env get-value CONTAINER_JOB_NAME)
rg_name=$(azd env get-value AZURE_RESOURCE_GROUP)

# Check if job exists
if az containerapp job show -g "$rg_name" --name "$job_name" &>/dev/null; then
    # Job exists, check if it has successful executions
    successful_count=$(az containerapp job execution list -g "$rg_name" --name "$job_name" --query "length([?properties.status=='Succeeded'])" -o tsv)
    if [ "$successful_count" -gt 0 ]; then
        echo "Container App Job already has $successful_count successful execution(s). Skipping..."
        exit 0
    else
        echo "Container App Job exists but has no successful executions. Continuing..."
    fi
else
    echo "Container App Job does not exist or could not be accessed. Continuing with deployment..."
fi
elif [ -z "$(azd env get-value SERVICE_FRONTEND_IMAGE_NAME)" ]; then
    echo "SERVICE_FRONTEND_IMAGE_NAME is null. Ensure your azd deployment succeeded. Exiting..."
    exit 1
else
    echo "Logging into Azure Container Registry..."
    az acr login --name $(azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT)

    # This is a workaround to the AZD limitation of updating the Container App Job
    # image after deployment of the services.
    echo "Updating container app job image..."
    az containerapp job update \
        -g $rg_name \
        --name $job_name \
        --image $(azd env get-value SERVICE_FRONTEND_IMAGE_NAME)

    echo "Starting job $job_name..."
    az containerapp job start \
        -g "$rg_name" \
        --name "$job_name"
    
    echo "Waiting for job to complete..."
    status="Running"
    while [[ "$status" == "Running" || "$status" == "Pending" ]]; do
        sleep 10
        # Get the latest execution
        execution=$(az containerapp job execution list -g "$rg_name" --name "$job_name" --query "[0]" -o json)
        status=$(echo $execution | jq -r .properties.status)
        
        # Show logs for current execution
        execution_name=$(echo $execution | jq -r .name)
        echo "Status: $status"
    done
    
    # Check if job completed successfully
    if [[ "$status" == "Succeeded" ]]; then
        echo "Job completed successfully."
    else
        echo "Job failed with status: $status"
        exit 1
    fi
fi

# Check if RUN_EVALS flag is set
if [ -z "${RUN_EVALS:-}" ]; then
    # RUN_EVALS is not set, prompt the user
    read -p "Would you like to run model evaluations through AI Foundry? (y/n): " response
    if [[ "$response" =~ ^[Yy] ]]; then
        echo "[Pytest Evals] Model evaluations will be run."
    else
        echo "[Pytest Evals] Model evaluations will be skipped."
        exit 0 
    fi
else
    echo "[Pytest Evals] RUN_EVALS flag is already set to: $RUN_EVALS"
fi
echo "Running pytest in tests/ directory..."
if [ -d "tests" ]; then
    cd tests || { echo "Failed to change to tests directory"; exit 1; }

    ## Due to current limitations with AI Hub Evals, we need to enable key-based auth temporarily on the storage account.
    # Get storage account name from environment variables
    storage_account=$(azd env get-value AZURE_STORAGE_ACCOUNT_NAME)

    if [ -z "$storage_account" ]; then
        echo "[Pytest Evals] Storage account name not found in environment variables. Skipping key access update."
    else
        echo "Enabling key-based access for storage account: $storage_account"
        az storage account update --name "$storage_account" --resource-group "$rg_name" --allow-shared-key-access true
        if [ $? -eq 0 ]; then
            echo "[Pytest Evals] Successfully enabled key-based access for storage account."
        else
            echo "[Pytest Evals] Failed to enable key-based access for storage account."
        fi
    fi
    
    # Declare variable to store test result
    test_result=0
    
    # Check if pytest is installed
    if command -v pytest &>/dev/null; then
        echo "Starting pytest..."
            exit 1
        fi
    else
        echo "pytest not found. Please install it with: pip install pytest"
        exit 1
    fi
else
    echo "tests directory not found!"
    exit 1
fi