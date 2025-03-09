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
