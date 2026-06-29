param(
    [string]$InstallRoot = "D:\CARLA",
    [switch]$SkipAdditionalMaps,
    [switch]$ForceDownload,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$CarlaVersion = "0.9.15"
$CarlaUrl = "https://tiny.carla.org/carla-0-9-15-windows"
$MapsUrl = "https://tiny.carla.org/additional-maps-0-9-15-windows"
$DownloadDir = Join-Path $InstallRoot "downloads"
$InstallDir = Join-Path $InstallRoot "CARLA_0.9.15"
$CarlaZip = Join-Path $DownloadDir "CARLA_0.9.15.zip"
$MapsZip = Join-Path $DownloadDir "AdditionalMaps_0.9.15.zip"

function Assert-FreeSpace {
    param([string]$PathRoot)
    $driveName = ([System.IO.Path]::GetPathRoot($PathRoot)).TrimEnd("\")
    $drive = Get-PSDrive -Name $driveName.TrimEnd(":")
    $requiredGb = if ($SkipAdditionalMaps) { 35 } else { 55 }
    $freeGb = [math]::Round($drive.Free / 1GB, 2)
    if ($freeGb -lt $requiredGb) {
        throw "Not enough free disk space on $driveName. Required: ${requiredGb}GB, free: ${freeGb}GB."
    }
}

function Download-File {
    param(
        [string]$Url,
        [string]$Destination
    )
    if ((Test-Path $Destination) -and -not $ForceDownload) {
        Write-Host "Using existing file: $Destination"
        return
    }
    Write-Host "Downloading $Url"
    Write-Host "Destination: $Destination"
    if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
        & curl.exe -k -L --fail --retry 5 --retry-delay 5 -o $Destination $Url
    }
    else {
        Start-BitsTransfer -Source $Url -Destination $Destination
    }
}

function Expand-Zip {
    param(
        [string]$ZipPath,
        [string]$Destination
    )
    Write-Host "Extracting $ZipPath to $Destination"
    Expand-Archive -Path $ZipPath -DestinationPath $Destination -Force
}

New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Assert-FreeSpace -PathRoot $InstallRoot

if ($DryRun) {
    Write-Host "Dry run only. No files will be downloaded or extracted."
    Write-Host "CARLA URL: $CarlaUrl"
    Write-Host "Additional Maps URL: $MapsUrl"
    Write-Host "Download directory: $DownloadDir"
    Write-Host "Install directory: $InstallDir"
    Write-Host "Skip Additional Maps: $SkipAdditionalMaps"
    exit 0
}

Download-File -Url $CarlaUrl -Destination $CarlaZip
Expand-Zip -ZipPath $CarlaZip -Destination $InstallDir

$Exe = Get-ChildItem -Path $InstallDir -Recurse -Filter "CarlaUE4.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $Exe) {
    throw "CARLA executable was not found after extraction under $InstallDir."
}

if (-not $SkipAdditionalMaps) {
    Download-File -Url $MapsUrl -Destination $MapsZip
    Expand-Zip -ZipPath $MapsZip -Destination $InstallDir
}

Write-Host ""
Write-Host "CARLA $CarlaVersion installation finished."
Write-Host "CARLA_HOME=$($Exe.Directory.FullName)"
Write-Host "Executable=$($Exe.FullName)"
Write-Host ""
Write-Host "Recommended environment variables:"
Write-Host "`$env:CARLA_HOME=`"$($Exe.Directory.FullName)`""
Write-Host "`$env:CARLA_HOST=`"127.0.0.1`""
Write-Host "`$env:CARLA_PORT=`"2000`""
