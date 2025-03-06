if ((azd env get-value CONTAINER_JOB_RUN) -eq "true") {
    Write-Output "Initialization job already run. Skipping..."
    exit 0
} else {
    # Define an array with the environment variable names that hold the job names.
    $jobs = @("CONTAINER_JOB_NAME" "CONTAINER_EVALUATION_NAME")

    $rg_name = azd env get-value RESOURCE_GROUP_NAME
    $acr_endpoint = azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT
    $image = azd env get-value SERVICE_FRONTEND_IMAGE_NAME

    Write-Output "Logging into Azure Container Registry..."
    az acr login --name $acr_endpoint

    foreach ($jobVar in $jobs) {
        $job_name = azd env get-value $jobVar

        Write-Output "Updating container app job image for job: $job_name..."
        az containerapp job update `
            -g $rg_name `
            --name $job_name `
            --image $image

        Write-Output "Starting job $job_name..."
        az containerapp job start `
            -g $rg_name `
            --name $job_name
    }

    azd env set CONTAINER_JOB_RUN true
    Write-Output "Jobs started successfully."
}