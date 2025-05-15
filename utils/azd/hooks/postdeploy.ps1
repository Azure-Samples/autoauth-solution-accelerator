# Simple logging functions
function Write-Info { param([string]$Message) Write-Host "[INFO] $Message" }
function Write-Error { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }
function Write-Warning { param([string]$Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }

# Get environment variables
Write-Info "Loading environment variables..."
$job_name = (azd env get-value CONTAINER_JOB_NAME).Trim()
$rg_name = (azd env get-value AZURE_RESOURCE_GROUP).Trim()
$frontend_image = (azd env get-value SERVICE_FRONTEND_IMAGE_NAME).Trim()
$acr_endpoint = (azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT).Trim()
$storage_account = (azd env get-value AZURE_STORAGE_ACCOUNT_NAME).Trim()

# Check if Container App Job exists
Write-Info "Checking if Container App Job exists and has successful executions..."
try {
    $null = az containerapp job show -g $rg_name --name $job_name 2>$null
    $successful_count = az containerapp job execution list -g $rg_name --name $job_name --query "length([?properties.status=='Succeeded'])" -o tsv

    if ([int]$successful_count -gt 0) {
        Write-Info "Container App Job already has $successful_count successful execution(s). Skipping..."
        $jobExists = $true
    } else {
        Write-Info "Container App Job exists but has no successful executions. Continuing..."
        $jobExists = $false
    }
} catch {
    Write-Info "Container App Job does not exist or could not be accessed. Continuing with deployment..."
    $jobExists = $false
}

# Update and run job if needed
if (-not $jobExists) {
    if ([string]::IsNullOrEmpty($frontend_image)) {
        Write-Error "SERVICE_FRONTEND_IMAGE_NAME is null. Ensure your azd deployment succeeded. Exiting..."
        exit 1
    }

    Write-Info "Logging into Azure Container Registry..."
    az acr login --name $acr_endpoint

    Write-Info "Updating container app job image..."
    $null = & az containerapp job update -g $rg_name --name $job_name --image $frontend_image --cpu 2.0 --memory 4.0 2>&1

    Write-Info "Starting job $job_name..."
    az containerapp job start -g $rg_name --name $job_name --cpu 2.0 --memory 4.0

    Write-Info "Waiting for job to complete..."
    $status = "Running"
    while ($status -eq "Running" -or $status -eq "Pending" -or $status -eq "Unknown") {
        Start-Sleep -Seconds 10
        $execution = az containerapp job execution list -g $rg_name --name $job_name --query "[0]" -o json | ConvertFrom-Json
        $status = $execution.properties.status
        Write-Info "Status: $status"
    }

    if ($status -ne "Succeeded") {
        Write-Error "Job failed with status: $status"
        exit 1
    }
    Write-Info "Job completed successfully."
}

# Run evaluations
if ([string]::IsNullOrEmpty($env:RUN_EVALS)) {
    $response = Read-Host "Would you like to run model evaluations through AI Foundry? (y/n)"
    if ($response -notmatch '^[Yy]') {
        Write-Info "Model evaluations will be skipped."
        exit 0
    }
    Write-Info "Model evaluations will be run."
} elseif ($env:RUN_EVALS -match '^[Ff][Aa][Ll][Ss][Ee]$') {
    Write-Info "RUN_EVALS is set to false. Skipping evaluations."
    exit 0
}

# Find project root
$current_dir = Get-Location
while ($true) {
    if (Test-Path -Path (Join-Path -Path $current_dir -ChildPath ".git") -PathType Container) {
        $project_root = $current_dir
        break
    }
    $parent_dir = Split-Path -Path $current_dir -Parent
    if ($parent_dir -eq $current_dir) {
        Write-Error ".git directory not found in any parent directory"
        exit 1
    }
    $current_dir = $parent_dir
}

Write-Info "Changing directory to project root: $project_root"
Set-Location -Path $project_root

if (-not (Test-Path -Path "tests" -PathType Container)) {
    Write-Error "Tests directory not found!"
    exit 1
}

# Enable key-based auth for storage account
if (-not [string]::IsNullOrEmpty($storage_account)) {
    Write-Info "Enabling key-based access for storage account: $storage_account"
    az storage account update --name $storage_account --resource-group $rg_name --allow-shared-key-access true | Out-Null
}

# Run tests
Write-Info "Starting pytest..."
try {
    pytest tests
    $test_result = $LASTEXITCODE
    if ($test_result -ne 0) {
        Write-Error "Tests failed."
    } else {
        Write-Info "Tests completed successfully."
    }
}
catch {
    Write-Error "Error running tests: $_"
    $test_result = 1
}

# Disable key-based auth for storage account
if (-not [string]::IsNullOrEmpty($storage_account)) {
    Write-Info "Disabling key-based access for storage account: $storage_account"
    az storage account update --name $storage_account --resource-group $rg_name --allow-shared-key-access false | Out-Null
}

exit $test_result
