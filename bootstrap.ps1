$ErrorActionPreference = "Stop"

$installRoot = Join-Path $env:LOCALAPPDATA "WhartonGrowthScorer"
$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("wharton-growth-scorer-" + [guid]::NewGuid().ToString("N"))
$archivePath = Join-Path $temporaryRoot "source.zip"
$extractRoot = Join-Path $temporaryRoot "extracted"
$sourceUrl = "https://github.com/kianjindal2010/wharton-growth-scorer/archive/refs/heads/main.zip"

try {
    New-Item -ItemType Directory -Force -Path $temporaryRoot, $extractRoot, $installRoot | Out-Null
    Write-Host "Downloading Wharton Growth Scorer..." -ForegroundColor Cyan
    Invoke-WebRequest -UseBasicParsing -Uri $sourceUrl -OutFile $archivePath
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractRoot -Force
    $sourceRoot = Get-ChildItem -LiteralPath $extractRoot -Directory | Select-Object -First 1
    if (-not $sourceRoot) { throw "The downloaded repository archive was empty." }
    Copy-Item -Path (Join-Path $sourceRoot.FullName "*") -Destination $installRoot -Recurse -Force
    & (Join-Path $installRoot "install.ps1")
    if ($LASTEXITCODE -ne 0) { throw "The installer returned exit code $LASTEXITCODE." }
    $launcherDir = Join-Path $env:LOCALAPPDATA "Programs\WhartonGrowthScorer\bin"
    if (($env:Path -split ";") -notcontains $launcherDir) {
        $env:Path = "$launcherDir;$env:Path"
    }
    Write-Host ""
    Write-Host "Ready. The Wharton Growth Scorer application has been opened." -ForegroundColor Green
    Write-Host "A shortcut is available on the Desktop and in the Start menu."
}
finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}
