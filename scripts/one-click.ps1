$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Jar = Join-Path $Root "game\nom2.jar"
if (-not (Test-Path $Jar)) {
    throw "game\nom2.jar not found. Put your NOM 2 JAR there first."
}

Write-Host "Preparing NOM 2 Android app for Galaxy S10..."
& (Join-Path $PSScriptRoot "setup.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "NOM 2 setup failed."
}

Push-Location (Join-Path $Root "engine")
try {
    Write-Host "Building self-contained NOM 2 APK..."
    & .\gradlew.bat :app:assembleOpenDebug
    if ($LASTEXITCODE -ne 0) {
        throw "APK build failed."
    }

    $apk = Get-ChildItem ".\app\build\outputs\apk\open\debug\*.apk" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($null -eq $apk) {
        throw "Built APK was not found."
    }

    $dist = Join-Path $Root "dist"
    New-Item -ItemType Directory -Force -Path $dist | Out-Null
    $finalApk = Join-Path $dist "NOM2-debug.apk"
    Copy-Item $apk.FullName $finalApk -Force

    Write-Host ""
    Write-Host "APK ready:"
    Write-Host "  $finalApk"
    Write-Host ""
    Write-Host "Install the APK manually on the Galaxy S10. No ADB/USB debugging was used."
} finally {
    Pop-Location
}
