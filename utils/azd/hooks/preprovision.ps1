# Retrieve current environment values (if they exist)
$enableEasyAuthVal = (& azd env get-value ENABLE_EASY_AUTH 2>$null) -replace "`r|`n", ""
$disableIngressVal = (& azd env get-value DISABLE_INGRESS 2>$null) -replace "`r|`n", ""

if ([string]::IsNullOrWhiteSpace($enableEasyAuthVal) -or [string]::IsNullOrWhiteSpace($disableIngressVal)) {
    while ($true) {
        $enableEasyAuthAnswer = Read-Host "Would you like to enable Easy Auth for your Container App? (y/n)"
        if ($enableEasyAuthAnswer -match '^[Yy]$') {
            & azd env set ENABLE_EASY_AUTH true
            & azd env set DISABLE_INGRESS false
            break
        }
        elseif ($enableEasyAuthAnswer -match '^[Nn]$') {
            Write-Host "===================================================================="
            Write-Host "⚠️  WARNING: You are deploying a publicly exposed frontend application"
            Write-Host "without authentication. This poses significant security risks!"
            Write-Host "===================================================================="
            while ($true) {
                $disableIngressAnswer = Read-Host "Would you like to disable ingress by default to mitigate this risk? (y/n)"
                if ($disableIngressAnswer -match '^[Yy]$') {
                    & azd env set ENABLE_EASY_AUTH false
                    & azd env set DISABLE_INGRESS true
                    break
                }
                elseif ($disableIngressAnswer -match '^[Nn]$') {
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
elseif ((& azd env get-value ENABLE_EASY_AUTH).Trim() -eq "true") {
    & azd env set DISABLE_INGRESS false
}
else {
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
