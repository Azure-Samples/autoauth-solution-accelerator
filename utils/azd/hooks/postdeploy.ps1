if ($(azd env get-value CONTAINER_JOB_RUN) -eq "true") {
    Write-Output "Initialization job already run. Skipping..."
    exit 0
  } else {
    $job_name = $(azd env get-value CONTAINER_JOB_NAME)
    $rg_name = $(azd env get-value RESOURCE_GROUP_NAME)
    Write-Output "Logging into Azure Container Registry..."
    az acr login --name $(azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT)
    Write-Output "Updating container app job image..."
    az containerapp job update `
        -g $rg_name `
        --name $job_name `
        --image $(azd env get-value SERVICE_FRONTEND_IMAGE_NAME)

    Write-Output "Starting the job to initialize the Search Index..."
    az containerapp job start `
        -g $(azd env get-value RESOURCE_GROUP_NAME) `
        --name $job_name

    azd env set CONTAINER_JOB_RUN true
    Write-Output "Job started successfully."
  }
