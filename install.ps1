$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $repoRoot ".venv"
$launcherDir = Join-Path $env:LOCALAPPDATA "Programs\WhartonGrowthScorer\bin"
$launcherPath = Join-Path $launcherDir "wharton.cmd"

Write-Host "Installing Wharton Growth Scorer..." -ForegroundColor Cyan

$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if (-not $pythonLauncher) {
    throw "Python was not found. Install Python 3.11 or 3.12 from https://python.org and select 'Add Python to PATH'."
}

if (-not (Test-Path (Join-Path $venvDir "Scripts\python.exe"))) {
    & py -3.12 -m venv $venvDir 2>$null
    if ($LASTEXITCODE -ne 0) {
        & py -3.11 -m venv $venvDir
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the Python environment with Python 3.11 or 3.12."
    }
}

$venvPython = Join-Path $venvDir "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Could not update pip." }
& $venvPython -m pip install -e $repoRoot
if ($LASTEXITCODE -ne 0) { throw "Could not install Growth Scorer." }

New-Item -ItemType Directory -Force -Path $launcherDir | Out-Null
$whartonExe = Join-Path $venvDir "Scripts\wharton.exe"
$launcher = "@echo off`r`n`"$whartonExe`" %*`r`n"
Set-Content -LiteralPath $launcherPath -Value $launcher -Encoding Ascii

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = @($userPath -split ";" | Where-Object { $_ })
if ($pathEntries -notcontains $launcherDir) {
    $newUserPath = (($pathEntries + $launcherDir) -join ";")
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
}

Write-Host ""
Write-Host "Installation complete." -ForegroundColor Green
Write-Host "Close and reopen PowerShell, then run: wharton predict"
Write-Host "Excel reports will be saved in: $HOME\Documents\Wharton Growth Scorer\output\scores"
