$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$OutputFile = Join-Path (Split-Path -Parent $ProjectRoot) "customer-analytics-hub-safe.zip"

Push-Location $ProjectRoot
try {
    git rev-parse --is-inside-work-tree | Out-Null
    git archive --format=zip --output=$OutputFile HEAD
    Write-Host "ZIP seguro criado em: $OutputFile"
    Write-Host "Somente arquivos versionados foram incluídos."
}
finally {
    Pop-Location
}
