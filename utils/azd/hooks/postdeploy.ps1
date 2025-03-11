# Requires PowerShell 7+
Set-StrictMode -Version Latest

# Assume these environment values are set similarly to the Bash script
$job_name        = azd env get-value CONTAINER_JOB_NAME
$rg_name         = azd env get-value AZURE_RESOURCE_GROUP
$frontend_image  = azd env get-value SERVICE_FRONTEND_IMAGE_NAME
$acr_endpoint    = azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT
$storage_account = azd env get-value AZURE_STORAGE_ACCOUNT_NAME

# Assume $project_root is set earlier (for example by a Find-ProjectRoot function)
# For this example, we use the current directory as the project root.
$project_root = Get-Location

function Test-ContainerJob {
    Write-Output "Checking if Container App Job exists and has successful executions..."
    try {
        # Check if job exists.
        az containerapp job show -g $rg_name --name $job_name | Out-Null
        # Job exists, check for successful executions.
        $successful_count = az containerapp job execution list -g $rg_name --name $job_name --query "length([?properties.status=='Succeeded'])" -o tsv
        if ([int]$successful_count -gt 0) {
            Write-Output "Container App Job already has $successful_count successful execution(s). Skipping..."
            return $true
        }
        Write-Output "Container App Job exists but has no successful executions. Continuing..."
        return $false
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
    # Change to project root directory.
    Write-Output "[Pytest Evals] Changing directory to project root: $project_root"
    Set-Location $project_root -ErrorAction Stop
    Write-Output "[Pytest Evals] Current directory: $(Get-Location)"

    # Ensure the "tests" directory exists.
    if (-not (Test-Path -Path "tests" -PathType Container)) {
        Write-Output "ERROR tests directory not found!"
        Write-Output "Current directory: $(Get-Location)"
        exit 1
    }

    # Enable key-based authentication for storage account, if defined.
    if (-not [string]::IsNullOrEmpty($storage_account)) {
        Write-Output "[Pytest Evals] Temporarily enabling key-based access for storage account: $storage_account"
        az storage account update --name $storage_account --resource-group $rg_name --allow-shared-key-access true | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Output "[Pytest Evals] Successfully enabled key-based access for storage account."
        }
        else {
            Write-Output "[Pytest Evals] Failed to enable key-based access for storage account."
        }
    }
    else {
        Write-Output "[Pytest Evals] Storage account name not found in environment variables. Skipping key access update."
    }

    # Run tests.
    $global:test_result = 0
    if (Get-Command pytest -ErrorAction SilentlyContinue) {
        Write-Output "[Pytest Evals] Starting pytest..."
        # Install dependencies if requirements.txt exists.
        if (Test-Path "requirements.txt") {
            Write-Output "[Pytest Evals] Checking requirements from requirements.txt..."
            pip install -r requirements.txt --quiet
            if ($LASTEXITCODE -ne 0) {
                Write-Output "[Pytest Evals] Failed to install required packages."
                $global:test_result = 1
            }
            else {
                Write-Output "[Pytest Evals] Requirements installed successfully."
            }
        }
        else {
            Write-Output "[Pytest Evals] No requirements.txt found. Proceeding without installing dependencies."
        }
        pytest tests
        if ($LASTEXITCODE -ne 0) {
            $global:test_result = 1
        }
    }
    else {
        Write-Output "[Pytest Evals] pytest not found. Please install it with: pip install pytest"
        $global:test_result = 1
    }

    # Always disable shared key access regardless of test results.
    if (-not [string]::IsNullOrEmpty($storage_account)) {
        Write-Output "[Pytest Evals] Disabling key-based access for storage account: $storage_account"
        az storage account update --name $storage_account --resource-group $rg_name --allow-shared-key-access false | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Output "[Pytest Evals] Successfully disabled key-based access for storage account."
        }
        else {
            Write-Output "[Pytest Evals] Failed to disable key-based access for storage account."
        }
    }

    # Exit with nonzero code if tests failed.
    if ($global:test_result -ne 0) {
        exit 1
    }
}

# Main execution flow
if (-not (Test-ContainerJob)) {
    Update-AndRunJob
}

Invoke-Evaluations
exit 0
