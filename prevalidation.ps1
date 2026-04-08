# prevalidation.ps1 — Adaptive Project Manager Submission Validator
#
# Checks that your HF Space is live, Docker image builds, and openenv validate passes.
#
# Prerequisites:
#   - Docker Desktop for Windows
#   - Python with openenv-core installed: pip install openenv-core
#
# Run:
#   .\prevalidation.ps1 -PingUrl "https://virustechhacks-adaptive-project-management.hf.space" [-RepoDir "."]
#
# Parameters:
#   PingUrl    Your HuggingFace Space URL
#   RepoDir    Path to your repo (default: current directory)
#
# Examples:
#   .\prevalidation.ps1 -PingUrl "https://virustechhacks-adaptive-project-management.hf.space"
#   .\prevalidation.ps1 -PingUrl "https://virustechhacks-adaptive-project-management.hf.space" -RepoDir "C:\path\to\repo"

param(
    [Parameter(Mandatory=$true, HelpMessage="Your HuggingFace Space URL")]
    [string]$PingUrl,
    
    [Parameter(Mandatory=$false)]
    [string]$RepoDir = "."
)

$ErrorActionPreference = "Stop"
$DockerBuildTimeout = 600

# Color functions
function Write-Pass { param($msg) Write-Host "[PASSED] -- $msg" -ForegroundColor Green }
function Write-Fail { param($msg) Write-Host "[FAILED] -- $msg" -ForegroundColor Red }
function Write-Hint { param($msg) Write-Host "  Hint: $msg" -ForegroundColor Yellow }
function Write-Step { param($msg) Write-Host $msg -ForegroundColor Cyan }

function Stop-Validation {
    param($step)
    Write-Host ""
    Write-Host "Validation stopped at $step. Fix the above before continuing." -ForegroundColor Red
    exit 1
}

# Validate repo directory
if (-not (Test-Path $RepoDir)) {
    Write-Host "Error: directory '$RepoDir' not found" -ForegroundColor Red
    exit 1
}
$RepoDir = Resolve-Path $RepoDir

# Remove trailing slash from URL
$PingUrl = $PingUrl.TrimEnd('/')

# Banner
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Adaptive Project Manager" -ForegroundColor Cyan
Write-Host "  Submission Validator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Repo:     $RepoDir"
Write-Host "Ping URL: $PingUrl"
Write-Host ""

$PassCount = 0

# ============================================================================
# Step 1: Ping HF Space
# ============================================================================
Write-Step "Step 1/3: Pinging HF Space ($PingUrl/reset) ..."

try {
    $response = Invoke-WebRequest -Uri "$PingUrl/reset" -Method POST `
        -ContentType "application/json" -Body '{}' `
        -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        Write-Pass "HF Space is live and responds to /reset"
        $PassCount++
    } else {
        Write-Fail "HF Space /reset returned HTTP $($response.StatusCode) (expected 200)"
        Write-Hint "Make sure your Space is running and the URL is correct."
        Write-Hint "Try opening $PingUrl in your browser first."
        Stop-Validation "Step 1"
    }
} catch {
    Write-Fail "HF Space not reachable (connection failed or timed out)"
    Write-Hint "Check your network connection and that the Space is running."
    Write-Hint "Error: $($_.Exception.Message)"
    Stop-Validation "Step 1"
}

# ============================================================================
# Step 2: Docker Build
# ============================================================================
Write-Step "Step 2/3: Running docker build ..."

# Check if docker is available
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Fail "docker command not found"
    Write-Hint "Install Docker Desktop: https://docs.docker.com/get-docker/"
    Stop-Validation "Step 2"
}

# Find Dockerfile
$DockerContext = $null
if (Test-Path "$RepoDir\Dockerfile") {
    $DockerContext = $RepoDir
} elseif (Test-Path "$RepoDir\server\Dockerfile") {
    $DockerContext = "$RepoDir\server"
} else {
    Write-Fail "No Dockerfile found in repo root or server\ directory"
    Stop-Validation "Step 2"
}

Write-Host "  Found Dockerfile in $DockerContext"

# Run docker build with timeout
try {
    $job = Start-Job -ScriptBlock {
        param($context)
        docker build $context 2>&1
    } -ArgumentList $DockerContext
    
    $completed = Wait-Job $job -Timeout $DockerBuildTimeout
    
    if ($null -eq $completed) {
        Stop-Job $job
        Remove-Job $job
        throw "Docker build timed out after ${DockerBuildTimeout}s"
    }
    
    $buildOutput = Receive-Job $job
    Remove-Job $job
    
    # Check if build succeeded (look for "Successfully built", "Successfully tagged", or "exporting to image")
    $buildSucceeded = $buildOutput | Where-Object { 
        $_ -match "Successfully (built|tagged)" -or 
        $_ -match "exporting to image" -or
        $_ -match "writing image sha256"
    }
    
    if ($buildSucceeded) {
        Write-Pass "Docker build succeeded"
        $PassCount++
    } else {
        Write-Fail "Docker build failed"
        Write-Host ($buildOutput | Select-Object -Last 20 | Out-String)
        Stop-Validation "Step 2"
    }
} catch {
    Write-Fail "Docker build failed: $($_.Exception.Message)"
    Stop-Validation "Step 2"
}

# ============================================================================
# Step 3: OpenEnv Validate
# ============================================================================
Write-Step "Step 3/3: Running openenv validate ..."

# Check if openenv is available (try both direct command and uv run)
$useUv = $false
if (-not (Get-Command openenv -ErrorAction SilentlyContinue)) {
    # Try uv run instead
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "  Using 'uv run openenv' (openenv not in PATH)"
        $useUv = $true
    } else {
        Write-Fail "openenv command not found"
        Write-Hint "Install it: pip install openenv-core"
        Write-Hint "Or use: uv pip install openenv-core"
        Stop-Validation "Step 3"
    }
}

# Run openenv validate
Push-Location $RepoDir
try {
    if ($useUv) {
        $validateOutput = & uv run openenv validate 2>&1
    } else {
        $validateOutput = & openenv validate 2>&1
    }
    $validateExitCode = $LASTEXITCODE
    
    if ($validateExitCode -eq 0) {
        Write-Pass "openenv validate passed"
        if ($validateOutput) {
            Write-Host "  $validateOutput"
        }
        $PassCount++
    } else {
        Write-Fail "openenv validate failed"
        Write-Host $validateOutput
        Stop-Validation "Step 3"
    }
} catch {
    Write-Fail "openenv validate failed: $($_.Exception.Message)"
    Stop-Validation "Step 3"
} finally {
    Pop-Location
}

# ============================================================================
# Success
# ============================================================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All 3/3 checks passed!" -ForegroundColor Green
Write-Host "  Your submission is ready to submit." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

exit 0
