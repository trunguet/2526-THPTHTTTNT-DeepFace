$ErrorActionPreference = "Stop"

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
}

Run-Step "Backend API tests" {
    $env:PYTHONPATH = "backend"
    python -m pytest backend\app\tests
}

Run-Step "Worker pipeline tests" {
    $env:PYTHONPATH = "worker"
    python -m pytest worker\app\tests
}

$CondaNodePath = Join-Path $env:USERPROFILE ".conda\envs\ltxldl"
$CondaNpmPath = Join-Path $CondaNodePath "npm.cmd"

if (Get-Command npm -ErrorAction SilentlyContinue) {
    $NpmCommand = "npm"
}
elseif (Test-Path $CondaNpmPath) {
    $env:PATH = "$CondaNodePath;$env:PATH"
    $NpmCommand = $CondaNpmPath
}
else {
    $NpmCommand = $null
}

if ($NpmCommand) {
    Run-Step "Admin frontend build" {
        Push-Location frontend\admin
        try {
            & $NpmCommand run build
        }
        finally {
            Pop-Location
        }
    }

    Run-Step "User frontend build" {
        Push-Location frontend\user
        try {
            & $NpmCommand run build
        }
        finally {
            Pop-Location
        }
    }
}
else {
    Write-Host ""
    Write-Host "Skipping frontend builds because npm was not found in PATH or ltxldl." -ForegroundColor Yellow
}
