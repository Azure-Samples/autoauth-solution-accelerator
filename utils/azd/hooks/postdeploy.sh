#!/bin/bash
set -e

# Get environment values once
job_name=$(azd env get-value CONTAINER_JOB_NAME)
rg_name=$(azd env get-value AZURE_RESOURCE_GROUP)
frontend_image=$(azd env get-value SERVICE_FRONTEND_IMAGE_NAME)
acr_endpoint=$(azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT)
storage_account=$(azd env get-value AZURE_STORAGE_ACCOUNT_NAME)

check_container_job() {
    echo "Checking if Container App Job exists and has successful executions..."

    # Check if job exists
    if az containerapp job show -g "$rg_name" --name "$job_name" &>/dev/null; then
        # Job exists, check if it has successful executions
        successful_count=$(az containerapp job execution list -g "$rg_name" --name "$job_name" --query "length([?properties.status=='Succeeded'])" -o tsv)
        if [ "$successful_count" -gt 0 ]; then
            echo "Container App Job already has $successful_count successful execution(s). Skipping..."
            return 0
        fi
        echo "Container App Job exists but has no successful executions. Continuing..."
        return 1
    else
        echo "Container App Job does not exist or could not be accessed. Continuing with deployment..."
        return 1
    fi
}

update_and_run_job() {
    if [ -z "$frontend_image" ]; then
        echo "SERVICE_FRONTEND_IMAGE_NAME is null. Ensure your azd deployment succeeded. Exiting..."
        exit 1
    fi

    echo "Logging into Azure Container Registry..."
    az acr login --name "$acr_endpoint"

    echo "Updating container app job image..."
    az containerapp job update -g "$rg_name" --name "$job_name" --image "$frontend_image"

    echo "Starting job $job_name..."
    az containerapp job start -g "$rg_name" --name "$job_name"

    echo "Waiting for job to complete..."
    status="Running"
    while [[ "$status" == "Running" || "$status" == "Pending" ]]; do
        sleep 10
        execution=$(az containerapp job execution list -g "$rg_name" --name "$job_name" --query "[0]" -o json)
        status=$(echo $execution | jq -r .properties.status)
        echo "Status: $status"
    done

    if [[ "$status" == "Succeeded" ]]; then
        echo "Job completed successfully."
    else
        echo "Job failed with status: $status"
        exit 1
    fi
}

run_evaluations() {
    if [ -z "${RUN_EVALS:-}" ]; then
        read -p "Would you like to run model evaluations through AI Foundry? (y/n): " response
        if [[ ! "$response" =~ ^[Yy] ]]; then
            echo "[Pytest Evals] Model evaluations will be skipped."
            return 0
        fi
        echo "[Pytest Evals] Model evaluations will be run."
    else
        echo "[Pytest Evals] RUN_EVALS flag is already set to: $RUN_EVALS"
    fi

    if [ ! -d "tests" ]; then
        echo "tests directory not found!"
        exit 1
    fi

    # Enable key-based auth for storage account
    if [ -n "$storage_account" ]; then
        echo "[Pytest Evals] Temporarily enabling key-based access for storage account: $storage_account"
        az storage account update --name "$storage_account" --resource-group "$rg_name" --allow-shared-key-access true ||
            echo "[Pytest Evals] Failed to enable key-based access for storage account."
    else
        echo "[Pytest Evals] Storage account name not found in environment variables. Skipping key access update."
    fi

    # Run tests
    test_result=0
    if command -v pytest &>/dev/null; then
        echo "[Pytest Evals] Starting pytest..."
        pytest tests || test_result=1
    else
        echo "[Pytest Evals] pytest not found. Please install it with: pip install pytest"
        test_result=1
    fi

    # Always disable shared key access regardless of results
    if [ -n "$storage_account" ]; then
        echo "[Pytest Evals] Disabling key-based access for storage account: $storage_account"
        az storage account update --name "$storage_account" --resource-group "$rg_name" --allow-shared-key-access false ||
            echo "[Pytest Evals] Failed to disable key-based access for storage account."
    fi

    # Exit with appropriate code
    if [ $test_result -ne 0 ]; then
        exit 1
    fi
}

# Main execution flow
if ! check_container_job; then
    update_and_run_job
fi

run_evaluations
exit 0
