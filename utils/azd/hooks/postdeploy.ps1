# Simple logging functions
function Write-Info { param([string]$Message) Write-Host "[INFO] $Message" }
function Write-Error { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

# Load environment variables
Write-Info "Loading environment variables..."
$indexer_hostname = (azd env get-value INDEXER_FUNCTION_APP_HOSTNAME 2>$null) | Select-Object -Last 1
$indexer_app_name = (azd env get-value INDEXER_FUNCTION_APP_NAME 2>$null) | Select-Object -Last 1
$rg_name = (azd env get-value AZURE_RESOURCE_GROUP 2>$null) | Select-Object -Last 1

if ([string]::IsNullOrWhiteSpace($indexer_hostname)) {
    Write-Error "INDEXER_FUNCTION_APP_HOSTNAME is not set. Ensure the indexer function app was deployed."
    exit 1
}
if ([string]::IsNullOrWhiteSpace($indexer_app_name) -or [string]::IsNullOrWhiteSpace($rg_name)) {
    Write-Error "INDEXER_FUNCTION_APP_NAME or AZURE_RESOURCE_GROUP is not set."
    exit 1
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
    Write-Error "Could not retrieve function key. Check your permissions on the function app."
    exit 1
}

# Wait for the function app to become reachable
$baseUrl = "https://$($indexer_hostname.Trim())"
Write-Info "Waiting for function app to become available (up to 180s)..."
$maxAttempts = 12
$delay = 15
for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    try {
        $probe = Invoke-WebRequest -Uri $baseUrl -Method Get -TimeoutSec 10 -ErrorAction SilentlyContinue
        Write-Info "Function app is responding (HTTP $($probe.StatusCode))."
        break
    } catch {
        $probeStatus = $_.Exception.Response.StatusCode.value__
        if ($probeStatus) {
            Write-Info "Function app is responding (HTTP $probeStatus)."
            break
        }
        Write-Info "Attempt $attempt/$maxAttempts - not ready yet, retrying in ${delay}s..."
        Start-Sleep -Seconds $delay
        if ($attempt -eq $maxAttempts) {
            Write-Error "Function app did not become available in time."
            exit 1
        }
    }
}

$url = "https://$($indexer_hostname.Trim())/api/reindex_all"
Write-Info "Invoking reindex_all at: $url"

$headers = @{
    "Content-Type"    = "application/json"
    "x-functions-key" = $func_key
}
$maxRetries = 3
$retryDelay = 20

for ($retry = 1; $retry -le $maxRetries; $retry++) {
    try {
        $response = Invoke-RestMethod -Uri $url -Method Post -Headers $headers -Body '{}' -TimeoutSec 600
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

Write-Error "reindex_all failed after $maxRetries attempts."
exit 1
