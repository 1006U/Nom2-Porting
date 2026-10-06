$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$ExpectedBranch = "galaxy-s10"
$CurrentBranch = (git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Could not determine the current Git branch."
}
if ($CurrentBranch -ne $ExpectedBranch) {
    throw "Wrong Git branch: '$CurrentBranch'. Switch first with: git switch galaxy-s10"
}

$Commit = (git rev-parse --short HEAD).Trim()
Write-Host "NOM 2 source branch: $CurrentBranch"
Write-Host "NOM 2 source commit: $Commit"

$Jar = Join-Path $Root "game\nom2.jar"
if (-not (Test-Path $Jar)) {
    throw "game\nom2.jar not found. Put your NOM 2 JAR there first."
}

$IconJpg = Join-Path $Root "overlay\icon.jpg"
$IconPng = Join-Path $Root "overlay\icon.png"
if (-not (Test-Path $IconJpg) -and -not (Test-Path $IconPng)) {
    Write-Warning "overlay\icon.jpg or overlay\icon.png was not found. The icon post-patch will search fallback locations."
}

Write-Host "Preparing NOM 2 Android app for Galaxy S10..."
& (Join-Path $PSScriptRoot "setup.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "NOM 2 setup failed."
}

$dist = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $dist | Out-Null
Remove-Item (Join-Path $dist "NOM2-debug.apk") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $dist "NOM2-port2-ko-s10-debug.apk") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $dist "NOM2-port3-ko-s10-debug.apk") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $dist "NOM2-port4-ko-s10-debug.apk") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $dist "NOM2-port5-ko-s10-debug.apk") -Force -ErrorAction SilentlyContinue

Push-Location (Join-Path $Root "engine")
try {
    Write-Host "Cleaning old Gradle outputs..."
    & .\gradlew.bat clean
    if ($LASTEXITCODE -ne 0) {
        throw "Gradle clean failed."
    }

    Write-Host "Building fresh self-contained NOM 2 APK..."
    & .\gradlew.bat :app:assembleOpenDebug --stacktrace
    if ($LASTEXITCODE -ne 0) {
        throw "APK build failed."
    }

    $apk = Get-ChildItem ".\app\build\outputs\apk\open\debug\*.apk" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($null -eq $apk) {
        throw "Built APK was not found."
    }

    $finalApk = Join-Path $dist "NOM2-debug.apk"
    $versionedApk = Join-Path $dist "NOM2-port5-ko-s10-debug.apk"
    Copy-Item $apk.FullName $finalApk -Force
    Copy-Item $apk.FullName $versionedApk -Force

    Write-Host ""
    Write-Host "Fresh APK ready:"
    Write-Host "  $finalApk"
    Write-Host "  $versionedApk"
    Write-Host ""
    Write-Host "Expected APK identity: versionName=1.0.43-port5-ko-s10, versionCode=105"
    Write-Host "Expected first-launch marker: nom2-port5-ko-s10-r4"
    Write-Host "Gameplay: tap anywhere to jump/action; bottom bar shows Pause only."
    Write-Host "Opening story: Korean patched; Korean font enlarged and anti-aliased."
    Write-Host "Online leaderboard: disabled/bypassed."
    Write-Host "Install this newly built APK manually on the Galaxy S10."
} finally {
    Pop-Location
}
