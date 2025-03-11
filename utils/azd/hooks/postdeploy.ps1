# Requires PowerShell 7+
Set-StrictMode -Version Latest

# Get environment values once
$job_name       = azd env get-value CONTAINER_JOB_NAME
$rg_name        = azd env get-value AZURE_RESOURCE_GROUP
$frontend_image = azd env get-value SERVICE_FRONTEND_IMAGE_NAME
$acr_endpoint   = azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT
$storage_account= azd env get-value AZURE_STORAGE_ACCOUNT_NAME

function Test-ContainerJob {
    Write-Output "Checking if Container App Job exists and has successful executions..."

    try {
        # Check if job exists
        az containerapp job show -g $rg_name --name $job_name | Out-Null
        # Job exists, check if it has successful executions
        $successful_count = az containerapp job execution list -g $rg_name --name $job_name --query "length([?properties.status=='Succeeded'])" -o tsv
        if ([int]$successful_count -gt 0) {
            Write-Output "Container App Job already has $successful_count successful execution(s). Skipping..."
            return $true
        }
        else {
            Write-Output "Container App Job exists but has no successful executions. Continuing..."
            return $false
        }
    }
    catch {
        Write-Output "Container App Job does not exist or could not be accessed. Continuing with deployment..."
        return $false
    }
}

function Update-AndRunJob {
    if ([string]::IsNullOrEmpty($frontend_image)) {
        Write-Output "SERVICE_FRONTEND_IMAGE_NAME is null. Ensure your azd deployment succeeded. Exiting..."
        exit 1
    }

    Write-Output "Logging into Azure Container Registry..."
    az acr login --name $acr_endpoint

    Write-Output "Updating container app job image..."
    az containerapp job update -g $rg_name --name $job_name --image $frontend_image

    Write-Output "Starting job $job_name..."
    az containerapp job start -g $rg_name --name $job_name

    Write-Output "Waiting for job to complete..."
    $status = "Running"
    while ($status -eq "Running" -or $status -eq "Pending") {
        Start-Sleep -Seconds 10
        $executionJson = az containerapp job execution list -g $rg_name --name $job_name --query "[0]" -o json
        $execution = $executionJson | ConvertFrom-Json
        $status = $execution.properties.status
        Write-Output "Status: $status"
    }

    if ($status -eq "Succeeded") {
        Write-Output "Job completed successfully."
    }
    else {
        Write-Output "Job failed with status: $status"
        exit 1
    }
}

function Invoke-Evaluations {
    if ([string]::IsNullOrEmpty($env:RUN_EVALS)) {
        $response = Read-Host "Would you like to run model evaluations through AI Foundry? (y/n)"
        if ($response -notmatch '^[Yy]') {
            Write-Output "[Pytest Evals] Model evaluations will be skipped."
            return
        }
        Write-Output "[Pytest Evals] Model evaluations will be run."
    }
    else {
        Write-Output "[Pytest Evals] RUN_EVALS flag is already set to: $env:RUN_EVALS"
    }

    if (-not (Test-Path -Path "tests" -PathType Container)) {
        Write-Output "tests directory not found!"
        exit 1
    }

    Set-Location "tests" -ErrorAction Stop

    # Enable key-based auth for storage account
    if (-not [string]::IsNullOrEmpty($storage_account)) {
        Write-Output "Enabling key-based access for storage account: $storage_account"
        try {
            az storage account update --name $storage_account --resource-group $rg_name --allow-shared-key-access true | Out-Null
        }
        catch {
            Write-Output "[Pytest Evals] Failed to enable key-based access for storage account."
        }
    }
    else {
        Write-Output "[Pytest Evals] Storage account name not found in environment variables. Skipping key access update."
    }

    # Run tests
    if (Get-Command pytest -ErrorAction SilentlyContinue) {
        Write-Output "Starting pytest..."
        pytest
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }
    else {
        Write-Output "pytest not found. Please install it with: pip install pytest"
        exit 1
    }
}

# Main execution flow
if (-not (Test-ContainerJob)) {
    Update-AndRunJob
}

Invoke-Evaluations
exit 0