[CmdletBinding()]
param()

# Enable strict mode and error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Constants and configuration
$ScriptName = (Get-Item $MyInvocation.MyCommand.Path).BaseName
$SpinnerChars = '|/-\'
$SpinnerDelay = 0.1

# Initialize logging
function Write-Log {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('INFO', 'WARN', 'ERROR')]
        [string]$Level,

        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $logMessage = "[$ScriptName] [$Level] $Message"

    if ($Level -eq 'ERROR') {
        Write-Error $logMessage
    } else {
        Write-Host $logMessage
    }
}

function Write-LogInfo {
    param([string]$Message)
    Write-Log -Level 'INFO' -Message $Message
}

function Write-LogError {
    param([string]$Message)
    Write-Log -Level 'ERROR' -Message $Message
}

function Write-LogWarning {
    param([string]$Message)
    Write-Log -Level 'WARN' -Message $Message
}

# Check required dependencies
function Test-Dependencies {
    Write-LogInfo "Checking required dependencies..."
    $missing = $false

    foreach ($cmd in @('az', 'pytest')) {
        if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
            Write-LogError "Required command not found: $cmd"
            $missing = $true
        }
    }

    # Check for equivalent of jq in PowerShell - we'll use ConvertFrom-Json

    if ($missing) {
        Write-LogError "Please install missing dependencies"
        return $false
    }

    return $true
}

# Load environment variables
function Get-EnvironmentVariables {
    Write-LogInfo "Loading environment variables..."
    $script:JobName = (& azd env get-value CONTAINER_JOB_NAME).Trim()
    $script:RgName = (& azd env get-value AZURE_RESOURCE_GROUP).Trim()
    $script:FrontendImage = (& azd env get-value SERVICE_FRONTEND_IMAGE_NAME).Trim()
    $script:AcrEndpoint = (& azd env get-value AZURE_CONTAINER_REGISTRY_ENDPOINT).Trim()
    $script:StorageAccount = (& azd env get-value AZURE_STORAGE_ACCOUNT_NAME).Trim()

    # Validate required variables
    if ([string]::IsNullOrEmpty($script:JobName) -or [string]::IsNullOrEmpty($script:RgName)) {
        Write-LogError "Required environment variables not set"
        return $false
    }

    return $true
}

# Find project root by searching for .git directory
function Get-ProjectRoot {
    $currentDir = Get-Location

    while ($true) {
        if (Test-Path -Path (Join-Path -Path $currentDir -ChildPath ".git") -PathType Container) {
            return $currentDir
        }

        $parentDir = Split-Path -Path $currentDir -Parent
        if ($parentDir -eq $currentDir) {
            Write-LogError ".git directory not found in any parent directory"
            return $null
        }

        $currentDir = $parentDir
    }
}

function Test-ContainerJob {
    Write-LogInfo "Checking if Container App Job exists and has successful executions..."

    # Check if job exists
    try {
        $null = & az containerapp job show -g $script:RgName --name $script:JobName 2>$null

        # Job exists, check for successful executions
        $successfulCount = (& az containerapp job execution list -g $script:RgName --name $script:JobName `
                --query "length([?properties.status=='Succeeded'])" -o tsv).Trim()

        if ([int]$successfulCount -gt 0) {
            Write-LogInfo "Container App Job already has $successfulCount successful execution(s). Skipping..."
            return $true
        }

        Write-LogInfo "Container App Job exists but has no successful executions. Continuing..."
        return $false
    }
    catch {
        Write-LogInfo "Container App Job does not exist or could not be accessed. Continuing with deployment..."
        return $false
    }
}

function Update-AndRunJob {
    if ([string]::IsNullOrEmpty($script:FrontendImage)) {
        Write-LogError "SERVICE_FRONTEND_IMAGE_NAME is null. Ensure your azd deployment succeeded. Exiting..."
        return $false
    }

    Write-LogInfo "Logging into Azure Container Registry..."
    & az acr login --name $script:AcrEndpoint

    Write-LogInfo "Updating container app job image..."
    & az containerapp job update -g $script:RgName --name $script:JobName --image $script:FrontendImage

    Write-LogInfo "Starting job $script:JobName..."
    & az containerapp job start -g $script:RgName --name $script:JobName

    Write-LogInfo "Waiting for job to complete..."
    $status = "Running"

    while ($status -eq "Running" -or $status -eq "Pending") {
        Start-Sleep -Seconds 10
        $executionJson = & az containerapp job execution list -g $script:RgName --name $script:JobName --query "[0]" -o json
        $execution = $executionJson | ConvertFrom-Json
        $status = $execution.properties.status
        Write-LogInfo "Status: $status"
    }

    if ($status -eq "Succeeded") {
        Write-LogInfo "Job completed successfully."
        return $true
    }
    else {
        Write-LogError "Job failed with status: $status"
        return $false
    }
}

# Display a spinner for long-running processes
function Show-Spinner {
    param([int]$ProcessId)

    $i = 0
    $spinnerLength = $SpinnerChars.Length

    while (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) {
        Write-Host "`r[$ScriptName] $($SpinnerChars[$i % $spinnerLength])" -NoNewline
        Start-Sleep -Milliseconds ($SpinnerDelay * 1000)
        $i++
    }

    # Clear the spinner line
    Write-Host "`r$((" " * 50))`r" -NoNewline
}

# Toggle storage account shared key access
function Set-StorageSharedKeyAccess {
    param(
        [bool]$Enable
    )

    if ([string]::IsNullOrEmpty($script:StorageAccount)) {
        Write-LogWarning "Storage account name not found in environment variables. Skipping key access update."
        return $true
    }

    $action = if ($Enable) { "Enabling" } else { "Disabling" }
    Write-LogInfo "$action key-based access for storage account: $script:StorageAccount"

    try {
        & az storage account update --name $script:StorageAccount --resource-group $script:RgName --allow-shared-key-access $Enable.ToString().ToLower() 2>$null
        $actionPast = if ($Enable) { "enabled" } else { "disabled" }
        Write-LogInfo "Successfully $actionPast key-based access."
        return $true
    }
    catch {
        $actionPresent = if ($Enable) { "enable" } else { "disable" }
        Write-LogError "Failed to $actionPresent key-based access."
        return $false
    }
}

function Invoke-Evaluations {
    # Ask user if they want to run evaluations (if not already set)
    if ([string]::IsNullOrEmpty($env:RUN_EVALS)) {
        $response = Read-Host "Would you like to run model evaluations through AI Foundry? (y/n)"
        if ($response -notmatch '^[Yy]') {
            Write-LogInfo "Model evaluations will be skipped."
            return $true
        }
        Write-LogInfo "Model evaluations will be run."
    }
    else {
        Write-LogInfo "RUN_EVALS flag is already set to: $env:RUN_EVALS"
        if ($env:RUN_EVALS -match '^[Ff][Aa][Ll][Ss][Ee]$') {
            Write-LogInfo "RUN_EVALS is set to false. Skipping evaluations."
            return $true
        }
    }

    # Change to project root directory
    $projectRoot = Get-ProjectRoot
    if (-not $projectRoot) {
        return $false
    }

    Write-LogInfo "Changing directory to project root: $projectRoot"
    try {
        Push-Location -Path $projectRoot
    }
    catch {
        Write-LogError "Failed to change directory to project root"
        return $false
    }

    if (-not (Test-Path -Path "tests" -PathType Container)) {
        Write-LogError "Tests directory not found! Current directory: $(Get-Location)"
        Pop-Location
        return $false
    }

    # Enable key-based auth for storage account
    Set-StorageSharedKeyAccess -Enable $true

    $testResult = $true

    # Install dependencies
    Write-LogInfo "Checking and installing dependencies..."
    if (Test-Path -Path "requirements.txt" -PathType Leaf) {
        try {
            & pip install -r requirements.txt --quiet
            Write-LogInfo "Dependencies installed."
        }
        catch {
            Write-LogError "Failed to install required packages."
            $testResult = $false
        }
    }
    else {
        Write-LogWarning "No requirements.txt found. Skipping dependency installation."
    }

    # Run tests
    if ($testResult) {
        Write-LogInfo "Starting pytest..."

        try {
            $process = Start-Process -FilePath pytest -ArgumentList "-s", "--color=yes", "tests" -PassThru -NoNewWindow

            # Start the spinner in a job
            $spinnerJob = Start-Job -ScriptBlock {
                param($processId, $scriptName, $spinnerChars, $spinnerDelay)

                $i = 0
                $spinnerLength = $spinnerChars.Length

                while (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
                    Write-Host "`r[$scriptName] $($spinnerChars[$i % $spinnerLength])" -NoNewline
                    Start-Sleep -Milliseconds ($spinnerDelay * 1000)
                    $i++
                }

                # Clear the spinner line
                Write-Host "`r$((" " * 50))`r" -NoNewline

            } -ArgumentList $process.Id, $ScriptName, $SpinnerChars, $SpinnerDelay

            # Wait for the process to complete
            $process.WaitForExit()

            # Stop the spinner job
            Stop-Job -Job $spinnerJob
            Remove-Job -Job $spinnerJob -Force

            if ($process.ExitCode -ne 0) {
                $testResult = $false
                Write-LogError "Tests failed."
            }
            else {
                Write-LogInfo "Tests completed successfully."
            }
        }
        catch {
            $testResult = $false
            Write-LogError "Error running tests: $_"
        }
    }

    # Disable shared key access
    Set-StorageSharedKeyAccess -Enable $false

    # Return to original directory
    Pop-Location

    return $testResult
}

# Main execution flow
function Invoke-Main {
    try {
        if (-not (Test-Dependencies)) {
            exit 1
        }

        if (-not (Get-EnvironmentVariables)) {
            exit 1
        }

        if (-not (Test-ContainerJob)) {
            if (-not (Update-AndRunJob)) {
                exit 1
            }
        }

        if (-not (Invoke-Evaluations)) {
            exit 1
        }

        exit 0
    }
    finally {
        # Ensure storage account key access is disabled
        if ($script:StorageAccount) {
            Set-StorageSharedKeyAccess -Enable $false | Out-Null
        }

        Write-LogInfo "Script finished"
    }
}

# Run the script
Invoke-Main
