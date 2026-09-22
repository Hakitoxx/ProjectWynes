<#
.SYNOPSIS
    Project Wynes - local setup (Method 2: GitHub ZIP download).

.DESCRIPTION
    Prepares the extracted repository for use:
      * validates the folder contents
      * finds a supported Python (3.11+)
      * creates a local .venv
      * installs the single dependency (PySide6) into it
      * verifies the app starts (headless smoke test)

    Afterwards, "projectwynes" inside this folder launches the app.
    Nothing outside this folder is modified.
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot

function Write-Step([string]$Text) { Write-Host "[wynes] $Text" }
function Fail([string]$Text) {
    Write-Host "[wynes] ERROR: $Text" -ForegroundColor Red
    exit 1
}

Write-Step "Project Wynes setup - $Root"

# ---------------------------------------------------------------- files
foreach ($required in @("run.py", "requirements.txt", "src\wynes")) {
    if (-not (Test-Path (Join-Path $Root $required))) {
        Fail "Required project file/folder missing: $required (incomplete download?)"
    }
}

# ------------------------------------------------------ prebuilt shortcut
if (Test-Path (Join-Path $Root "dist\projectwynes.exe")) {
    Write-Step "Prebuilt executable found (dist\projectwynes.exe) - nothing to install."
    Write-Step "You can now run:  projectwynes"
    exit 0
}

# ---------------------------------------------------------------- python
# @(<exe>, <extra args...>) - executable goes first, any launcher flags after
$PythonCmd = $null
foreach ($candidate in @(@("py", "-3"), @("python"), @("python3"))) {
    $exe = Get-Command $candidate[0] -ErrorAction SilentlyContinue
    if (-not $exe) { continue }
    $rest = @($candidate | Select-Object -Skip 1)
    $versionOut = & $exe.Source @rest "--version" 2>$null
    if ($versionOut -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]; $minor = [int]$Matches[2]
        if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 11)) {
            $PythonCmd = @($exe.Source) + $rest
            Write-Step "Found Python $major.$minor ($($exe.Source))"
            break
        }
    }
}
if (-not $PythonCmd) {
    Fail "Python 3.11+ was not found. Install it from https://www.python.org/downloads/ (enable the 'Add python.exe to PATH' option), then run this setup again."
}

# ------------------------------------------------------------------ venv
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Step "Creating virtual environment (.venv) ..."
    & $PythonCmd[0] @($PythonCmd | Select-Object -Skip 1) -m venv (Join-Path $Root ".venv")
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
        Fail "Could not create the virtual environment."
    }
} else {
    Write-Step "Virtual environment already exists."
}

# ------------------------------------------------------------- dependencies
Write-Step "Installing dependencies (PySide6) ..."
& $VenvPython -m pip install --disable-pip-version-check -r (Join-Path $Root "requirements.txt")
if ($LASTEXITCODE -ne 0) { Fail "Dependency installation failed (network problem?)." }

# ---------------------------------------------------------------- verify
Write-Step "Verifying installation (headless smoke test) ..."
$env:QT_QPA_PLATFORM = "offscreen"
& $VenvPython (Join-Path $Root "run.py") --smoke-test
if ($LASTEXITCODE -ne 0) { Fail "Smoke test failed." }
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "[wynes] Setup complete. / Kurulum tamamlandi." -ForegroundColor Green
Write-Host "[wynes] Start the app with: projectwynes        (CMD, in this folder)"
Write-Host "[wynes] PowerShell:               .\projectwynes.cmd"
