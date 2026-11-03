<#
.SYNOPSIS
  Copies the migration AI toolkit (Duo skills + Python tools) into a cloned app repo.

.EXAMPLE
  .\tools\install-to-app-repo.ps1 -AppRepo C:\work\claims-portal
  .\tools\install-to-app-repo.ps1 -AppRepo C:\work\claims-portal -InstallPython

  Run it again after the AI repo changes; it overwrites the toolkit files only.
#>
param(
    [Parameter(Mandatory = $true)][string]$AppRepo,
    [switch]$InstallPython
)
$ErrorActionPreference = 'Stop'
$AiRepo = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path (Join-Path $AppRepo '.git'))) { throw "$AppRepo is not a git repo (no .git folder). Clone the app repo first." }

$items = @(
    '.agents\skills',
    'tools\doc-prep',
    'tools\office-export'
)
foreach ($i in $items) {
    $src = Join-Path $AiRepo $i
    $dst = Join-Path $AppRepo $i
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
    Copy-Item -Path (Join-Path $src '*') -Destination $dst -Recurse -Force
    Write-Host "copied $i"
}
New-Item -ItemType Directory -Force -Path (Join-Path $AppRepo 'docs') | Out-Null

if ($InstallPython) {
    python -m pip install -r (Join-Path $AppRepo 'tools\doc-prep\requirements.txt') -r (Join-Path $AppRepo 'tools\office-export\requirements.txt')
}

Write-Host ""
Write-Host "Done. Next:"
Write-Host "  1. Copy the Confluence exports (Word/PDF/HTML/images/draw.io) into e.g. $AppRepo\docs\confluence"
Write-Host "  2. Open $AppRepo in VS Code -> GitLab Duo Chat -> new conversation -> /skills (check they're listed)"
Write-Host "  3. /functional-doc docs/confluence"
