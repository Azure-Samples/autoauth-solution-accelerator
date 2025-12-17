# ============================================================================
# AZURE LOCATION CHECK - Must be set before provisioning
# ============================================================================

$validLocations = @("eastus2", "swedencentral", "southcentralus", "canadaeast", "eastus", "francecentral", "japaneast", "norwayeast", "polandcentral", "southindia", "switzerlandnorth", "uksouth", "westus3")

function Get-CleanAzdValue {
    param([string]$key)
    $output = & azd env get-value $key 2>$null
    if ($LASTEXITCODE -eq 0) {
        if ($output -match "^([^\r\n]+)") {
            return $Matches[1].Trim()
        }
    }
    return ""
}

$azureLocation = Get-CleanAzdValue "AZURE_LOCATION"

if ([string]::IsNullOrEmpty($azureLocation)) {
    Write-Host "======================================="
    Write-Host "⚠️  AZURE_LOCATION is not set"
    Write-Host "======================================="
    Write-Host ""
    Write-Host "Azure OpenAI is only available in specific regions."
    Write-Host "Valid locations: $($validLocations -join ' ')"
    Write-Host ""
    
    while ($true) {
        $locationChoice = Read-Host "Enter Azure location (default: eastus2)"
        
        # Use default if empty
        if ([string]::IsNullOrEmpty($locationChoice)) {
            $azureLocation = "eastus2"
            break
        }
        
        # Validate input
        if ($validLocations -contains $locationChoice) {
            $azureLocation = $locationChoice
            break
        }
        else {
            Write-Host "❌ Invalid location: '$locationChoice'"
            Write-Host "Valid locations: $($validLocations -join ' ')"
            Write-Host ""
        }
    }
    
    & azd env set AZURE_LOCATION $azureLocation
    Write-Host ""
    Write-Host "✅ AZURE_LOCATION set to: $azureLocation"
    Write-Host ""
}
else {
    if ($validLocations -notcontains $azureLocation) {
        Write-Host "======================================="
        Write-Host "❌ ERROR: Invalid AZURE_LOCATION: $azureLocation"
        Write-Host "======================================="
        Write-Host ""
        Write-Host "Valid locations are: $($validLocations -join ' ')"
        Write-Host ""
        Write-Host "Please run: azd env set AZURE_LOCATION <valid-location>"
        exit 1
    }
    Write-Host "✅ AZURE_LOCATION: $azureLocation"
}

# ============================================================================
# USER AND GIT INFO
# ============================================================================

# Get current user ID and git hash
$currentUserClientId = (& az ad signed-in-user show --query id -o tsv).Trim()
$gitHash = (& git rev-parse --short HEAD).Trim()

# Set environment variables
& azd env set PRINCIPAL_ID $currentUserClientId
& azd env set GIT_HASH $gitHash

# Display information
Write-Host "======================================="
Write-Host " Current User Client ID: $currentUserClientId"
Write-Host " Git Commit Hash:        $gitHash"
Write-Host "======================================="

# (Get-CleanAzdValue function already defined above)

# Get clean values
$enableEasyAuth = Get-CleanAzdValue "ENABLE_EASY_AUTH"
$disableIngress = Get-CleanAzdValue "DISABLE_INGRESS"

if ([string]::IsNullOrEmpty($enableEasyAuth) -or [string]::IsNullOrEmpty($disableIngress)) {
    while ($true) {
        $enableEasyAuth = Read-Host "Would you like to enable Easy Auth for your Container App? (y/n)"
        if ($enableEasyAuth -match '^[Yy]$') {
            & azd env set ENABLE_EASY_AUTH true
            & azd env set DISABLE_INGRESS false
            break
        }
        elseif ($enableEasyAuth -match '^[Nn]$') {
            Write-Host "===================================================================="
            Write-Host "⚠️  WARNING: You are deploying a publicly exposed frontend application"
            Write-Host "without authentication. This poses significant security risks!"
            Write-Host "===================================================================="

            while ($true) {
                $disableIngress = Read-Host "Would you like to disable ingress by default to mitigate this risk? (y/n)"
                if ($disableIngress -match '^[Yy]$') {
                    & azd env set ENABLE_EASY_AUTH false
                    & azd env set DISABLE_INGRESS true
                    break
                }
                elseif ($disableIngress -match '^[Nn]$') {
                    # User doesn't want to disable ingress
                    & azd env set ENABLE_EASY_AUTH false
                    & azd env set DISABLE_INGRESS false
                    break
                }
                else {
                    Write-Host "Please enter 'y' or 'n'."
                }
            }
            break
        }
        else {
            Write-Host "Please enter 'y' or 'n'."
        }
    }
}
elseif ($enableEasyAuthVal -eq "true") {
    # If Easy Auth is enabled, ensure ingress is not disabled
    & azd env set DISABLE_INGRESS false
    Write-Host "Easy Auth is enabled. Ensuring ingress is not disabled."
}
else {
    # Display current settings
    $currentEasyAuth = (& azd env get-value ENABLE_EASY_AUTH).Trim()
    $currentDisableIngress = (& azd env get-value DISABLE_INGRESS).Trim()

    Write-Host "======================================="
    Write-Host "Environment variables already set:"
    Write-Host " ENABLE_EASY_AUTH: $currentEasyAuth"
    Write-Host " DISABLE_INGRESS:  $currentDisableIngress"
    Write-Host "To change these settings, run:"
    Write-Host "  azd env set ENABLE_EASY_AUTH <true|false>"
    Write-Host "  azd env set DISABLE_INGRESS <true|false>"
    Write-Host "======================================="
}
