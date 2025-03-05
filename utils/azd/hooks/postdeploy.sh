#!/bin/bash
# set -x

echo "Checking for Initialization Flag to run Job..."
if [ "$(azd env get-value CONTAINER_JOB_RUN)" = "true" ]; then
    echo "Initialization job already run. Skipping..."
    exit 0
elif [ -z "$(azd env get-value SERVICE_FRONTEND_IMAGE_NAME)" ]; then
    echo "SERVICE_FRONTEND_IMAGE_NAME is null. Ensure your azd deployment succeeded. Exiting..."
    exit 1
else
    echo "Logging into Azure Container Registry..."
    az acr login --name "$(azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT)"
    rg_name=$(azd env get-value RESOURCE_GROUP_NAME)
    image=$(azd env get-value SERVICE_FRONTEND_IMAGE_NAME)

    # Array of job name environment variables.
    jobs=("CONTAINER_JOB_NAME" "CONTAINER_EVALUATION_AGENTIC" "CONTAINER_EVALUATION_AUTO_DETERMINATION" "CONTAINER_EVALUATION_CLINICAL_EXTRACTOR")

    for job_var in "${jobs[@]}"; do
        job_name=$(azd env get-value "$job_var")

        echo "Updating container app job image for job: $job_name..."
        az containerapp job update \
            -g "$rg_name" \
            --name "$job_name" \
            --image "$image"

        echo "Starting job $job_name..."
        az containerapp job start \
            -g "$rg_name" \
            --name "$job_name"
    done

    azd env set CONTAINER_JOB_RUN true
    echo "Jobs started successfully."
fi