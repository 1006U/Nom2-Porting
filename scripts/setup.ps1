param(
    [string]$Jar = "game/nom2.jar",
    [string]$Engine = "engine"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Upstream = "https://github.com/nikita36078/J2ME-Loader.git"
$Tag = "1.8.2"

function Resolve-AndroidSdkPath {
    $Candidates = @()
    if ($env:ANDROID_HOME) { $Candidates += $env:ANDROID_HOME }
    if ($env:ANDROID_SDK_ROOT) { $Candidates += $env:ANDROID_SDK_ROOT }
    if ($env:LOCALAPPDATA) { $Candidates += (Join-Path $env:LOCALAPPDATA "Android\Sdk") }
    if ($env:USERPROFILE) { $Candidates += (Join-Path $env:USERPROFILE "AppData\Local\Android\Sdk") }

    foreach ($Candidate in ($Candidates | Select-Object -Unique)) {
        if ([string]::IsNullOrWhiteSpace($Candidate)) { continue }
        $Expanded = [Environment]::ExpandEnvironmentVariables($Candidate)
        if (Test-Path -LiteralPath $Expanded -PathType Container) {
            return (Resolve-Path -LiteralPath $Expanded).Path
        }
    }
    return $null
}

function Ensure-AndroidLocalProperties {
    param([string]$EnginePath)
    $LocalProperties = Join-Path $EnginePath "local.properties"

    if (Test-Path -LiteralPath $LocalProperties) {
        $Existing = Get-Content -LiteralPath $LocalProperties -ErrorAction SilentlyContinue
        foreach ($Line in $Existing) {
            if ($Line -match '^\s*sdk\.dir\s*=\s*(.+?)\s*$') {
                $RawPath = $Matches[1].Trim() -replace '\\:', ':'
                $RawPath = $RawPath -replace '\\\\', '\'
                $RawPath = $RawPath -replace '/', '\'
                if (Test-Path -LiteralPath $RawPath -PathType Container) {
                    Write-Host "Using Android SDK from existing local.properties: $RawPath"
                    return
                }
            }
        }
    }

    $SdkPath = Resolve-AndroidSdkPath
    if (-not $SdkPath) {
        throw @"
Android SDK location was not found.

Install/open Android Studio once and make sure Android SDK is installed, then rerun this script.
Expected Windows location is usually:
  $env:LOCALAPPDATA\Android\Sdk

You can also set ANDROID_HOME or ANDROID_SDK_ROOT manually.
"@
    }

    $GradleSdkPath = $SdkPath -replace '\\', '/'
    "sdk.dir=$GradleSdkPath" | Set-Content -LiteralPath $LocalProperties -Encoding ASCII
    Write-Host "Android SDK detected: $SdkPath"
    Write-Host "Created: $LocalProperties"
}

if (-not (Test-Path $Jar)) {
    throw ("NOM 2 JAR not found: " + $Jar + [Environment]::NewLine + "Place your legally obtained game at game/nom2.jar.")
}

if (-not (Test-Path (Join-Path $Engine ".git"))) {
    Write-Host "Cloning J2ME Loader $Tag..."
    git clone --depth 1 --branch $Tag $Upstream $Engine
    if ($LASTEXITCODE -ne 0) { throw "Could not clone J2ME Loader." }
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
        if ($LASTEXITCODE -ne 0) { throw ("Could not restore upstream engine file: " + $File) }
    }
}

Ensure-AndroidLocalProperties -EnginePath $Engine

Write-Host "Checking icon resize dependency (Pillow)..."
$PillowInstalled = python -c "import importlib.util; print('yes' if importlib.util.find_spec('PIL') else 'no')"
if ($LASTEXITCODE -ne 0) { throw "Python could not check for Pillow." }
if ($PillowInstalled.Trim() -ne "yes") {
    python -m pip install --user Pillow
    if ($LASTEXITCODE -ne 0) { throw "Could not install Pillow. Run manually: python -m pip install --user Pillow" }
}

$PatchedJar = "game/generated/nom2-ko.jar"
Write-Host "Creating Korean NOM 2 JAR..."
python tools/patch_korean.py --input $Jar --output $PatchedJar
if ($LASTEXITCODE -ne 0) { throw "NOM 2 Korean patch failed." }

Write-Host "Preparing Galaxy S10 NOM 2 engine..."
python tools/prepare_engine.py --engine $Engine --jar $PatchedJar
if ($LASTEXITCODE -ne 0) { throw "NOM 2 engine patch failed." }

Write-Host "Applying Galaxy S10 touch/buttons/original-icon fixes..."
python tools/post_patch_ui.py --engine $Engine
if ($LASTEXITCODE -ne 0) { throw "NOM 2 Galaxy S10 UI post-patch failed." }

Write-Host "Disabling obsolete online leaderboard..."
python tools/disable_leaderboard.py --engine $Engine
if ($LASTEXITCODE -ne 0) { throw "NOM 2 leaderboard bypass patch failed." }

Write-Host "Finalizing screen-aware Galaxy S10 controls..."
python tools/finalize_s10_controls.py --engine $Engine
if ($LASTEXITCODE -ne 0) { throw "NOM 2 final Galaxy S10 controls patch failed." }

Write-Host ""
Write-Host "NOM 2 port workspace is ready."
Write-Host "Primary real-device target: Samsung Galaxy S10"
Write-Host "Korean patch: enabled (including opening story)"
Write-Host "Original artwork launcher icon: enabled"
Write-Host "Gameplay touch anywhere: jump/action"
Write-Host "Gameplay bottom control: Pause only"
Write-Host "Menu/story buttons: screen-aware"
Write-Host "Online leaderboard: disabled/bypassed"
Write-Host "Open '$Engine' in Android Studio, or run:"
Write-Host "  cd $Engine"
Write-Host "  .\gradlew.bat :app:assembleOpenDebug"
