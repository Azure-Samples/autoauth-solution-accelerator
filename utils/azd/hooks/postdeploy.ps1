# Simple logging functions
function Write-Info { param([string]$Message) Write-Host "[INFO] $Message" }
function Write-Warn { param([string]$Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Error { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

function Test-StrictPostdeploy {
    $strictMode = [string]::Concat($env:POSTDEPLOY_STRICT)
    return $strictMode -match '^(?i:true|1|yes)$'
}

function Resolve-PostdeployFailure {
    param([string]$Message)

    if (Test-StrictPostdeploy) {
        Write-Error $Message
        return $false
    }

    Write-Warn $Message
    Write-Warn "Continuing because POSTDEPLOY_STRICT is not enabled. Re-run utils/azd/hooks/postdeploy.ps1 later if you want to bootstrap the indexer after deployment."
    return $true
}

function Get-FunctionKeyViaArm {
    try {
        $subscriptionId = (az account show --query id -o tsv 2>$null) | Select-Object -Last 1
        if ([string]::IsNullOrWhiteSpace($subscriptionId)) { return $null }

        return (az rest `
            --method post `
            --url "https://management.azure.com/subscriptions/$($subscriptionId.Trim())/resourceGroups/$($rg_name.Trim())/providers/Microsoft.Web/sites/$($indexer_app_name.Trim())/host/default/listkeys?api-version=2024-04-01" `
            --query "functionKeys.default" -o tsv 2>$null) | Select-Object -Last 1
    } catch {
        return $null
    }
}

function Wait-ForFunctionApp {
    param([string]$FunctionKey)

    $baseUrl = "https://$($indexer_hostname.Trim())/api/health?code=$FunctionKey"
    Write-Info "Waiting for function app health endpoint to become available (up to 180s)..."
    $maxAttempts = 12
    $delay = 15
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        try {
            $probe = Invoke-WebRequest -Uri $baseUrl -Method Get -TimeoutSec 10 -ErrorAction Stop
            Write-Info "Function app endpoint is responding (HTTP $($probe.StatusCode))."
            return $true
        } catch {
            $probeStatus = $_.Exception.Response.StatusCode.value__
            if ($probeStatus -in 200, 401, 403) {
                Write-Info "Function app endpoint is responding (HTTP $probeStatus)."
                return $true
            }

            Write-Info "Attempt $attempt/$maxAttempts - not ready yet, retrying in ${delay}s..."
            Start-Sleep -Seconds $delay
        }
    }

    return $false
}

# Load environment variables
Write-Info "Loading environment variables..."
$indexer_hostname = (azd env get-value INDEXER_FUNCTION_APP_HOSTNAME 2>$null) | Select-Object -Last 1
$indexer_app_name = (azd env get-value INDEXER_FUNCTION_APP_NAME 2>$null) | Select-Object -Last 1
$frontend_container_name = (azd env get-value FRONTEND_CONTAINER_NAME 2>$null) | Select-Object -Last 1
$rg_name = (azd env get-value AZURE_RESOURCE_GROUP 2>$null) | Select-Object -Last 1

if ([string]::IsNullOrWhiteSpace($indexer_hostname)) {
    Write-Error "INDEXER_FUNCTION_APP_HOSTNAME is not set. Ensure the indexer function app was deployed."
    exit 1
}
if ([string]::IsNullOrWhiteSpace($indexer_app_name) -or [string]::IsNullOrWhiteSpace($rg_name)) {
    Write-Error "INDEXER_FUNCTION_APP_NAME or AZURE_RESOURCE_GROUP is not set."
    exit 1
}
if ([string]::IsNullOrWhiteSpace($frontend_container_name)) {
    Write-Error "FRONTEND_CONTAINER_NAME is not set. Ensure the frontend container app was deployed."
    exit 1
}

function Sync-FrontendFunctionAccess {
    param([string]$FunctionKey)

    $secretName = "indexer-function-key"
    Write-Info "Syncing Function App access into frontend container app $($frontend_container_name.Trim())..."

    az containerapp secret set `
        --name $frontend_container_name.Trim() `
        --resource-group $rg_name.Trim() `
        --secrets "$secretName=$FunctionKey" *> $null

    az containerapp update `
        --name $frontend_container_name.Trim() `
        --resource-group $rg_name.Trim() `
        --set-env-vars `
            "INDEXER_FUNCTION_KEY=secretref:$secretName" `
            "INDEXER_FUNCTION_BASE_URL=https://$($indexer_hostname.Trim())" `
            "INDEXER_FUNCTION_APP_HOSTNAME=$($indexer_hostname.Trim())" *> $null

    Write-Info "Frontend container app updated with indexer function access."
}

# Fetch function host key
Write-Info "Fetching function host key for $($indexer_app_name.Trim())..."
$func_key = $null
try {
    # Use Select-Object -Last 1 to strip any spurious warnings the az CLI may print to stdout
    $func_key = (az functionapp keys list --name $indexer_app_name.Trim() --resource-group $rg_name.Trim() --query "functionKeys.default" -o tsv 2>$null) | Select-Object -Last 1
} catch { }
if ([string]::IsNullOrWhiteSpace($func_key)) {
    try {
        $func_key = (az functionapp keys list --name $indexer_app_name.Trim() --resource-group $rg_name.Trim() --query "masterKey" -o tsv 2>$null) | Select-Object -Last 1
    } catch { }
}
if ([string]::IsNullOrWhiteSpace($func_key)) {
    $func_key = Get-FunctionKeyViaArm
}
if ([string]::IsNullOrWhiteSpace($func_key)) {
    if (-not (Resolve-PostdeployFailure -Message "Could not retrieve function key. Check your permissions on the function app, or re-run postdeploy once the function host is ready.")) {
        exit 1
    }
    exit 0
}

try {
    Sync-FrontendFunctionAccess -FunctionKey $func_key
} catch {
    if (-not (Resolve-PostdeployFailure -Message "Failed to sync Function App access into the frontend container app.")) {
        exit 1
    }
    exit 0
}

if (-not (Wait-ForFunctionApp -FunctionKey $func_key)) {
    if (-not (Resolve-PostdeployFailure -Message "Function app did not become available in time.")) {
        exit 1
    }
    exit 0
}

$url = "https://$($indexer_hostname.Trim())/api/reindex_all?code=$func_key"
Write-Info "Invoking reindex_all at: $url"

$headers = @{
    "Content-Type"    = "application/json"
    "x-functions-key" = $func_key
}
$maxRetries = 3
$retryDelay = 20

for ($retry = 1; $retry -le $maxRetries; $retry++) {
    try {
        $response = Invoke-RestMethod -Uri $url -Method Post -Headers $headers -Body '{"prefix":"policies_ocr/"}' -TimeoutSec 600
        Write-Info "reindex_all completed successfully."
        Write-Info "Response: $($response | ConvertTo-Json -Depth 5 -Compress)"
        Write-Info "Post-deploy finished."
        exit 0
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Info "Attempt $retry/$maxRetries failed (HTTP $statusCode): $($_.Exception.Message)"
        if ($retry -lt $maxRetries) {
            Write-Info "Retrying in ${retryDelay}s..."
            Start-Sleep -Seconds $retryDelay
        }
    }
}

if (-not (Resolve-PostdeployFailure -Message "reindex_all failed after $maxRetries attempts.")) {
    exit 1
}
exit 0
