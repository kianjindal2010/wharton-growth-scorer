$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvDir = Join-Path $repoRoot ".venv"
$launcherDir = Join-Path $env:LOCALAPPDATA "Programs\WhartonGrowthScorer\bin"
$launcherPath = Join-Path $launcherDir "wharton.cmd"
$startMenuShortcut = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Wharton Growth Scorer.lnk"
$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "Wharton Growth Scorer.lnk"

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

$guiExe = Join-Path $venvDir "Scripts\wharton-app.exe"
if (-not (Test-Path -LiteralPath $guiExe)) {
    throw "The desktop application launcher was not installed."
}
$shell = New-Object -ComObject WScript.Shell
foreach ($shortcutPath in @($startMenuShortcut, $desktopShortcut)) {
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $guiExe
    $shortcut.WorkingDirectory = $repoRoot
    $shortcut.IconLocation = "$guiExe,0"
    $shortcut.Description = "Wharton Growth Scorer"
    $shortcut.Save()
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = @($userPath -split ";" | Where-Object { $_ })
if ($pathEntries -notcontains $launcherDir) {
    $newUserPath = (($pathEntries + $launcherDir) -join ";")
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
}

Write-Host ""
Write-Host "Installation complete." -ForegroundColor Green
Write-Host "Open 'Wharton Growth Scorer' from the Desktop or Start menu." -ForegroundColor Green
Write-Host "Advanced command-line access remains available with: wharton predict"
Write-Host "Excel reports will be saved in: $HOME\Documents\Wharton Growth Scorer\output\scores"
Start-Process -FilePath $guiExe -WorkingDirectory $repoRoot
