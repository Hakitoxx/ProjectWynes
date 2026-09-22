<#
.SYNOPSIS
    Project Wynes - uninstaller (Method 1 installations).

.DESCRIPTION
    Removes the Project Wynes installation directory and its (and only its)
    entry from the CURRENT USER PATH. Nothing else is touched.
#>
[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "ProjectWynes")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$bin = Join-Path $InstallDir "bin"

Get-Process -Name "projectwynes" -ErrorAction SilentlyContinue | Stop-Process -Force

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath) {
    $keep = $userPath -split ";" | Where-Object {
        $_ -and $_.TrimEnd("\") -ine $bin.TrimEnd("\")
    }
    [Environment]::SetEnvironmentVariable("Path", ($keep -join ";"), "User")
    Write-Host "[wynes] Removed PATH entry: $bin"
}

if ($InstallDir -match "ProjectWynes" -and (Test-Path -LiteralPath $InstallDir)) {
    Remove-Item -LiteralPath $InstallDir -Recurse -Force
    Write-Host "[wynes] Removed $InstallDir"
}

Write-Host "[wynes] Uninstalled. Open a new terminal for the PATH change to apply."
