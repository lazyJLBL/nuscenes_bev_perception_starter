param(
    [string]$EnvName = "carla0915",
    [string]$PythonVersion = "3.7.9"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    throw "conda was not found. Install Anaconda/Miniconda or provide CARLA_BRIDGE_PYTHON manually."
}

$envList = conda env list | Out-String
if ($envList -match "^\s*$EnvName\s") {
    Write-Host "Conda environment '$EnvName' already exists."
}
else {
    Write-Host "Creating conda environment '$EnvName' with Python $PythonVersion"
    conda create -y -n $EnvName python=$PythonVersion
}

$pythonOutput = conda run -n $EnvName python -c "import sys; print(sys.executable)"
$pythonPath = ($pythonOutput -split "`r?`n" | Where-Object { $_.Trim() } | Select-Object -Last 1).Trim()
Write-Host "CARLA bridge Python: $pythonPath"
Write-Host "Set this before starting the backend:"
Write-Host "`$env:CARLA_BRIDGE_PYTHON=`"$pythonPath`""
