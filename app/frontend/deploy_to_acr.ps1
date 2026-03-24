<#
.SYNOPSIS
    Deploy the frontend container image to an existing Azure Container Registry.

.DESCRIPTION
    Uses `az acr build` for a cloud-based build and push (no local Docker needed).

.PARAMETER Registry
    Name of the Azure Container Registry (required).

.PARAMETER ImageName
    Image name (default: autoauth-frontend).

.PARAMETER Tag
    Image tag (default: latest).

.EXAMPLE
    .\app\frontend\deploy_to_acr.ps1 -Registry myregistry
    .\app\frontend\deploy_to_acr.ps1 -Registry myregistry -ImageName autoauth-frontend -Tag v1.2.0
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$Registry,

    [string]$ImageName = "autoauth-frontend",

    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "../..")
$Dockerfile = Join-Path $RepoRoot "app/frontend/Dockerfile"

# Verify az CLI is available
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI (az) is not installed."
}

# Verify logged in
az account show 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Not logged in to Azure. Run 'az login' first."
}

Write-Host "=== Frontend Container Build & Push ==="
Write-Host "  Registry:   $Registry"
Write-Host "  Image:      ${ImageName}:${Tag}"
Write-Host "  Dockerfile: $Dockerfile"
Write-Host "  Context:    $RepoRoot"
Write-Host ""

az acr build `
    --registry $Registry `
    --image "${ImageName}:${Tag}" `
    --file $Dockerfile `
    $RepoRoot

if ($LASTEXITCODE -ne 0) {
    Write-Error "az acr build failed."
}

Write-Host ""
Write-Host "Done. Image pushed to ${Registry}.azurecr.io/${ImageName}:${Tag}"
