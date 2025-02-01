<#
.SYNOPSIS
This script compiles Bicep files to ARM templates and generates corresponding documentation.
.DESCRIPTION
The script takes in a directory of Bicep files, compiles them into ARM templates and then generates markdown documentation for each ARM template.
The markdown files are then merged into a single file and copied to the destination path provided.
.PARAMETER BicepDirectory
Specifies the directory containing Bicep files. This parameter is mandatory.
# .PARAMETER DestinationFile
# Specifies the destination path including the filename where the final merged documentation markdown file will be copied. This parameter is mandatory.
.EXAMPLE
PS> .\Script.ps1 -BicepDirectory "path\to\bicep\files" -DestinationFile "path\to\destination"
#>
param (
    [Parameter(Mandatory=$false)] [string] $BicepDirectory = 'infra'
    # [Parameter(Mandatory=$true)] [string] $DestinationFile
)

$compiledDir = "$BicepDirectory"
$docDir = "$BicepDirectory"
# $mergedMdFilename = "MergedDocumentation.md"

if (!(Test-Path $compiledDir)) {
    New-Item -ItemType Directory -Force -Path $compiledDir
}

if (!(Test-Path $docDir)) {
    New-Item -ItemType Directory -Force -Path $docDir
}

$bicepDir = Resolve-Path $BicepDirectory
$ignorePatterns = @('*.test.bicep', 'main.parameters.json')

Get-ChildItem -Path $bicepDir -Filter "*.bicep" -Recurse | ForEach-Object {
    $ignore = $false
    foreach ($pattern in $ignorePatterns) {
        if ($_.Name -like $pattern) {
            $ignore = $true
            break
        }
    }
    if ($ignore) {
        Write-Host "Ignoring file: $($_.FullName)"
        return
    }

    $jsonFileName = $_.BaseName + '.json'
    $relativeDir = [IO.Path]::GetRelativePath($bicepDir.Path, $_.DirectoryName)
    if (!(Test-Path "$compiledDir/$relativeDir")) {
        New-Item -ItemType Directory -Force -Path "$compiledDir/$relativeDir"
    }
    Write-Host "Attempting to compile Bicep file to ARM template..."
    try {
        & 'az' 'bicep' 'build' '-f' $_.FullName '--outfile' "$compiledDir/$relativeDir/$jsonFileName"
        Write-Host "Successfully compiled Bicep file to ARM template: $compiledDir/$relativeDir/$jsonFileName"
    }
    catch {
        Write-Host "Failed to compile Bicep file: $_"
        continue
    }
}

$compiledDir = Resolve-Path $compiledDir
Get-ChildItem -Path $compiledDir -Filter '*.json' -Recurse | ForEach-Object {
    $ignore = $false
    foreach ($pattern in $ignorePatterns) {
        # Translate Bicep ignore patterns into JSON patterns
        $jsonPattern = $pattern -replace '\.bicep$', '.json'
        if ($_.Name -like $jsonPattern) {
            Write-Host "Ignoring file: $($_.FullName)"
            $ignore = $true
            break
        }
    }
    if ($ignore) {
        return
    }

    $markdownFileName = $_.BaseName
    $relativeDir = [IO.Path]::GetRelativePath($compiledDir, $_.DirectoryName)
    if (!(Test-Path "$docDir/$relativeDir")) {
        New-Item -ItemType Directory -Force -Path "$docDir/$relativeDir"
    }
    try {
        Invoke-PSDocument -Module PSDocs.Azure -OutputPath "$docDir/$relativeDir" -InputObject $_.FullName -Culture 'en-US' -InstanceName $markdownFileName
        $markdownFilePath = "$docDir/$relativeDir/$markdownFileName.md"
        if (Test-Path $markdownFilePath) {
            $content = Get-Content -Path $markdownFilePath
            if ($content -ne $null -and $content.Trim() -ne '') {
                $content = $content -replace '# Azure template', "# $markdownFileName"

                # Extract default values from the ARM template
                $armTemplate = Get-Content -Path $_.FullName -Raw | ConvertFrom-Json
                $parameters = $armTemplate.parameters
                if ($parameters) {
                    $defaultValues = @()
                    foreach ($param in $parameters.PSObject.Properties) {
                        if ($param.Value.defaultValue) {
                            $defaultValues += "`r`n- **$($param.Name)**: $($param.Value.defaultValue)"
                        }
                    }
                    if ($defaultValues.Count -gt 0) {
                        $content += "`r`n## Default Values`r`n"
                        $content += $defaultValues -join "`r`n"
                    }
                }

                Set-Content -Path $markdownFilePath -Value $content
            } else {
                Remove-Item -Path $markdownFilePath -Force
            }
        }
    }
    catch {
        Write-Host "Error generating documentation for $($_.FullName): $_"
    }
}

# Include the base directory along with all subdirectories
$directories = [System.Collections.ArrayList]@((Get-Item -Path $docDir))
$directories += Get-ChildItem -Path $docDir -Directory -Recurse

$directories | ForEach-Object {
    $mdFiles = Get-ChildItem -Path $_.FullName -Filter "*.md" -File -ErrorAction SilentlyContinue
    $mergeCandidates = $mdFiles | Where-Object { $_.Name -ne "README.md" }

    if ($mergeCandidates.Count -gt 0) {
        $readmeFilePath = Join-Path $_.FullName "README.md"
        if (Test-Path $readmeFilePath) {
            Remove-Item $readmeFilePath -Force
        }
        New-Item -ItemType File -Force -Path $readmeFilePath | Out-Null
        Add-Content -Path $readmeFilePath -Value "# Documentation for the Bicep modules in this directory`r`n"
        Add-Content -Path $readmeFilePath -Value "`r`n"
        $toc = "## Table of Contents`r`n"
        $index = 0

        $mergeCandidates | ForEach-Object {
            $indexString = if ($index -eq 0) { "" } else { "-$index" }
            $toc += "- [$($_.BaseName)](#$($_.BaseName.ToLower()))`r`n"
            $toc += "  - [Parameters](#parameters$indexString)`r`n"
            $toc += "  - [Outputs](#outputs$indexString)`r`n"
            $toc += "  - [Snippets](#snippets$indexString)`r`n"
            $index++
        }
        Add-Content -Path $readmeFilePath -Value $toc

        $mergeCandidates | ForEach-Object {
            $content = Get-Content $_.FullName
            Add-Content -Path $readmeFilePath -Value $content
        }

        $mergeCandidates | ForEach-Object {
            Remove-Item -Path $_.FullName -Force
        }
    }
}
