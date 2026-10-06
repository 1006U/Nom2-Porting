param(
    [string]$Jar = "game/nom2.jar",
    [string]$Engine = "engine"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Upstream = "https://github.com/nikita36078/J2ME-Loader.git"
$Tag = "1.8.2"

if (-not (Test-Path $Jar)) {
    throw ("NOM 2 JAR not found: " + $Jar + [Environment]::NewLine + "Place your legally obtained game at game/nom2.jar.")
}

if (-not (Test-Path (Join-Path $Engine ".git"))) {
    Write-Host "Cloning J2ME Loader $Tag..."
    git clone --depth 1 --branch $Tag $Upstream $Engine
    if ($LASTEXITCODE -ne 0) {
        throw "Could not clone J2ME Loader."
    }
} else {
    Write-Host "Using existing engine checkout: $Engine"
    Write-Host "Refreshing upstream files patched by NOM 2..."
    $PatchedUpstreamFiles = @(
        "build.gradle",
        "app/build.gradle",
        "app/src/main/AndroidManifest.xml",
        "app/src/main/java/ru/playsoftware/j2meloader/config/Config.java",
        "app/src/main/java/ru/woesss/j2me/installer/AppInstaller.java",
        "app/src/main/java/javax/microedition/lcdui/Canvas.java"
    )
    foreach ($File in $PatchedUpstreamFiles) {
        git -C $Engine checkout -- $File
        if ($LASTEXITCODE -ne 0) {
            throw ("Could not restore upstream engine file: " + $File)
        }
    }
}

Write-Host "Preparing Galaxy S10 NOM 2 engine..."
python tools/prepare_engine.py --engine $Engine --jar $Jar
if ($LASTEXITCODE -ne 0) {
    throw "NOM 2 engine patch failed."
}

Write-Host ""
Write-Host "NOM 2 port workspace is ready."
Write-Host "Primary real-device target: Samsung Galaxy S10"
Write-Host "Open '$Engine' in Android Studio, or run:"
Write-Host "  cd $Engine"
Write-Host "  .\gradlew.bat :app:assembleOpenDebug"
