$ErrorActionPreference = "Stop"

$backendPath = Join-Path $PSScriptRoot "backend"
$frontendPath = Join-Path $PSScriptRoot "frontend"
$backendUrl = "http://127.0.0.1:8000/docs"
$frontendUrl = "http://127.0.0.1:5173/"
$pythonPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

function Test-PythonRuntime {
    param([string]$Path)

    try {
        & $Path -c "import fastapi, osmnx, uvicorn" *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

if (-not (Test-PythonRuntime $pythonPath)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and (Test-PythonRuntime $pythonCommand.Source)) {
        $pythonPath = $pythonCommand.Source
        Write-Host "Using the installed Python because the project virtual environment is unavailable."
    }
    else {
        throw "A working Python environment with the project dependencies was not found. Run the setup commands in README.md."
    }
}

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    throw "npm was not found. Install Node.js to run the frontend."
}

function Test-Endpoint {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 3 -UseBasicParsing
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

if (-not (Test-Endpoint $backendUrl)) {
    Write-Host "Starting the backend. Loading the street network can take a minute..."
    $backendProcess = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $backendPath `
        -PassThru

    $timer = [Diagnostics.Stopwatch]::StartNew()
    $lastNotice = 0
    while (-not (Test-Endpoint $backendUrl)) {
        $backendProcess.Refresh()
        $backendChildProcesses = Get-CimInstance Win32_Process `
            -Filter "ParentProcessId = $($backendProcess.Id)" `
            -ErrorAction SilentlyContinue
        if ($backendProcess.HasExited -and -not $backendChildProcesses) {
            throw "The backend exited during startup. Check its terminal for the error."
        }
        if ($timer.Elapsed.TotalSeconds -ge 300) {
            throw "The backend did not become ready within 5 minutes. Check its terminal for errors."
        }
        if ($timer.Elapsed.TotalSeconds -ge $lastNotice + 15) {
            Write-Host "Still loading the street network ($([int]$timer.Elapsed.TotalSeconds)s)..."
            $lastNotice = [int]$timer.Elapsed.TotalSeconds
        }
        Start-Sleep -Seconds 3
    }
}
else {
    Write-Host "Backend is already running."
}

if (-not (Test-Endpoint $frontendUrl)) {
    Write-Host "Starting the frontend..."
    Start-Process `
        -FilePath $npmCommand.Source `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1") `
        -WorkingDirectory $frontendPath

    $timer = [Diagnostics.Stopwatch]::StartNew()
    while (-not (Test-Endpoint $frontendUrl)) {
        if ($timer.Elapsed.TotalSeconds -ge 60) {
            throw "The frontend did not become ready within 1 minute. Check its terminal for errors."
        }
        Start-Sleep -Seconds 2
    }
}
else {
    Write-Host "Frontend is already running."
}

Write-Host "BeatTheHeat is ready at $frontendUrl"
Start-Process $frontendUrl
