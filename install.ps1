<#
.SYNOPSIS
    Project Wynes - PowerShell installer (Method 1).

.DESCRIPTION
    Installs Project Wynes for the CURRENT Windows user (no admin needed):

      1. Downloads the official release package from the Project Wynes
         GitHub releases page (HTTPS, official URLs only). With -SourceZip
         a local package file is used instead (offline/testing).
      2. Verifies the package against its published SHA-256 checksum.
      3. Installs to %LOCALAPPDATA%\ProjectWynes.
      4. Creates the "projectwynes" launcher in ...\ProjectWynes\bin.
      5. Adds that folder to the USER PATH (only if missing).

    Open a NEW terminal afterwards and run:  projectwynes

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File install.ps1 -SourceZip .\projectwynes-windows.zip
#>
[CmdletBinding()]
param(
    [string]$SourceZip = "",
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "ProjectWynes"),
    [switch]$NoPathEdit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoBase  = "https://github.com/Hakitoxx/ProjectWynes"
$AssetName = "projectwynes-windows.zip"
$ShaName   = "$AssetName.sha256"

function Info([string]$Text) { Write-Host "[wynes] $Text" }
function Die([string]$Text) {
    Write-Host "[wynes] ERROR: $Text" -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------ main steps
Write-Host "----------------------------------------"
Write-Host "  Project Wynes installer"
Write-Host "----------------------------------------"

$work = Join-Path ([IO.Path]::GetTempPath()) ("wynes-install-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $work | Out-Null

try {
    # ------------------------------------------------- obtain package
    if ($SourceZip) {
        if (-not (Test-Path -LiteralPath $SourceZip)) { Die "Package not found: $SourceZip" }
        $package = (Resolve-Path -LiteralPath $SourceZip).Path
        $checksum = "$package.sha256"
        if (-not (Test-Path -LiteralPath $checksum)) {
            Die "Missing checksum file next to the package: expected '$checksum'"
        }
        Info "Using local package: $package"
    } else {
        $package  = Join-Path $work $AssetName
        $checksum = Join-Path $work $ShaName
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        foreach ($pair in @(@("$RepoBase/releases/latest/download/$AssetName", $package),
                            @("$RepoBase/releases/latest/download/$ShaName", $checksum))) {
            Info "Downloading $($pair[0])"
            try {
                Invoke-WebRequest -Uri $pair[0] -OutFile $pair[1] -UseBasicParsing -TimeoutSec 300
            } catch {
                Die ("Download failed: {0}`n     Is a v1.2.0+ release published on GitHub? " +
                     "Alternatively run 'git clone' or use the ZIP method. Details: {1}") -f $pair[0], $_.Exception.Message
            }
        }
    }

    # ------------------------------------------------- checksum verify
    if ((Get-Item -LiteralPath $package).Length -lt 1MB) {
        Die "Downloaded package is suspiciously small - aborting."
    }
    $expectedLine = (Get-Content -LiteralPath $checksum -TotalCount 1).Trim()
    $expected = ($expectedLine -split "\s+")[0].ToLowerInvariant()
    if ($expected -notmatch "^[0-9a-f]{64}$") { Die "Checksum file is malformed." }
    $actual = (Get-FileHash -LiteralPath $package -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expected) {
        Die "Checksum mismatch!`n     expected: $expected`n     actual:   $actual`n     The package was NOT installed."
    }
    Info "Checksum verified: $actual"

    # ------------------------------------------------- stop running app
    $running = Get-Process -Name "projectwynes" -ErrorAction SilentlyContinue
    if ($running) {
        Info "Stopping the running Project Wynes instance..."
        $running | Stop-Process -Force
        Start-Sleep -Seconds 1
    }

    # ------------------------------------------------- install payload
    if ($InstallDir -notmatch "ProjectWynes") {
        Die "Refusing non-standard install directory: $InstallDir"
    }
    if (Test-Path -LiteralPath $InstallDir) {
        Info "Replacing previous installation..."
        Remove-Item -LiteralPath $InstallDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
    Expand-Archive -LiteralPath $package -DestinationPath $InstallDir -Force

    $exe = Join-Path $InstallDir "projectwynes.exe"
    if (-not (Test-Path -LiteralPath $exe)) {
        Die "Package is invalid: projectwynes.exe missing after extraction."
    }

    # ------------------------------------------------- launcher + PATH
    $binDir = Join-Path $InstallDir "bin"
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
    $launcher = Join-Path $binDir "projectwynes.cmd"
    $launcherLines = @(
        "@echo off"
        "rem Project Wynes launcher (generated by install.ps1)"
        ('start "" "{0}" %*' -f $exe)
    )
    Set-Content -LiteralPath $launcher -Encoding ASCII -Value ($launcherLines -join "`r`n")
    Info "Launcher created: $launcher"

    # tiny uninstaller next to the app
    $uninstaller = Join-Path $InstallDir "uninstall.ps1"
    $uninstallLines = @(
        'param([string]$InstallDir = (Join-Path $env:LOCALAPPDATA "ProjectWynes"))'
        'Set-StrictMode -Version Latest'
        '$ErrorActionPreference = "Stop"'
        '$bin = Join-Path $InstallDir "bin"'
        'Get-Process -Name "projectwynes" -ErrorAction SilentlyContinue | Stop-Process -Force'
        '$userPath = [Environment]::GetEnvironmentVariable("Path", "User")'
        'if ($userPath) {'
        '    $keep = $userPath -split ";" | Where-Object { $_ -and $_.TrimEnd("\") -ine $bin.TrimEnd("\") }'
        '    [Environment]::SetEnvironmentVariable("Path", ($keep -join ";"), "User")'
        '}'
        'if ($InstallDir -match "ProjectWynes" -and (Test-Path -LiteralPath $InstallDir)) {'
        '    Remove-Item -LiteralPath $InstallDir -Recurse -Force'
        '}'
        'Write-Host "Project Wynes removed. Open a new terminal for the PATH change to apply."'
    )
    Set-Content -LiteralPath $uninstaller -Encoding ASCII -Value ($uninstallLines -join "`r`n")

    if (-not $NoPathEdit) {
        $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
        $entries = @()
        if ($userPath) { $entries = $userPath -split ";" | Where-Object { $_ } }
        $already = $entries | Where-Object { $_.TrimEnd("\") -ieq $binDir.TrimEnd("\") }
        if (-not $already) {
            $newPath = (@($entries) + $binDir) -join ";"
            [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
            Info "Added to your user PATH: $binDir"
        } else {
            Info "User PATH already contains $binDir - unchanged."
        }
    }

    Info "Installation complete: $InstallDir"
    Write-Host ""
    Write-Host "  Open a NEW Command Prompt or PowerShell window and run:"
    Write-Host ""
    Write-Host "      projectwynes"
    Write-Host ""
    Write-Host "  (PATH changes apply to new terminals only.)"
    Write-Host "  Uninstall:  $uninstaller"
}
finally {
    if (Test-Path -LiteralPath $work) {
        Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
    }
}
