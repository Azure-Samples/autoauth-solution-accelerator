Write-Output "Checking if Container App Job exists and has successful executions..."
$job_name = azd env get-value CONTAINER_JOB_NAME
$rg_name = azd env get-value AZURE_RESOURCE_GROUP

# Check if job exists
# $jobOutput = az containerapp job show -g $rg_name --name $job_name 2>$null
# if ($LASTEXITCODE -eq 0) {
#     $successful_count = az containerapp job execution list -g $rg_name --name $job_name --query "length([?properties.status=='Succeeded'])" -o tsv
#     if ([int]$successful_count -gt 0) {
#         Write-Output "Container App Job already has $successful_count successful execution(s). Skipping..."
#         exit 0
#     }
#     else {
#         Write-Output "Container App Job exists but has no successful executions. Continuing..."
#     }
# }
# else {
#     Write-Output "Container App Job does not exist or could not be accessed. Continuing with deployment..."
# }

# Check if SERVICE_FRONTEND_IMAGE_NAME is set
$svcImageName = azd env get-value SERVICE_FRONTEND_IMAGE_NAME
if (-not $svcImageName) {
    Write-Output "SERVICE_FRONTEND_IMAGE_NAME is null. Ensure your azd deployment succeeded. Exiting..."
    exit 1
}

Write-Output "Logging into Azure Container Registry..."
$acrEndpoint = azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT
az acr login --name $acrEndpoint

# Workaround to update container app job image after service deployment.
Write-Output "Updating container app job image..."
az containerapp job update -g $rg_name --name $job_name --image $svcImageName

Write-Output "Starting job $job_name..."
az containerapp job start -g $rg_name --name $job_name

Write-Output "Waiting for job to complete..."
$status = "Running"
while ($status -eq "Running" -or $status -eq "Pending") {
    Start-Sleep -Seconds 10
    # Get the latest execution
    $execution = az containerapp job execution list -g $rg_name --name $job_name --query "[0]" -o json | ConvertFrom-Json
    $status = $execution.properties.status
    $execution_name = $execution.name
    Write-Output "$execution_name Status: $status"
}

if ($status -eq "Succeeded") {
    Write-Output "Job completed successfully."
}
else {
    Write-Output "Job failed with status: $status"
    exit 1
}
