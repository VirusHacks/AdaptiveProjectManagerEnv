# Prevalidation Scripts

This directory contains validation scripts to verify your submission before final submission.

## Scripts

### `prevalidation.ps1` (Windows PowerShell - Recommended for Windows)

PowerShell script optimized for Windows development environments.

**Usage:**
```powershell
.\prevalidation.ps1 -PingUrl "https://virustechhacks-adaptive-project-management.hf.space"
```

**What it checks:**
1. ✅ HF Space is live and responding (hits `/reset` endpoint)
2. ✅ Docker build succeeds
3. ✅ OpenEnv validation passes

**Requirements:**
- Docker Desktop for Windows
- Python with `openenv-core` (or `uv` with dependencies installed)

### `prevalidation.sh` (Bash - For Linux/Mac/WSL)

Bash script for Unix-like environments.

**Usage:**
```bash
chmod +x prevalidation.sh
./prevalidation.sh https://virustechhacks-adaptive-project-management.hf.space
```

**Requirements:**
- Docker
- `openenv` command in PATH
- `curl`

## Validation Results

All 3/3 checks passed! ✅

```
[PASSED] -- HF Space is live and responds to /reset
[PASSED] -- Docker build succeeded  
[PASSED] -- openenv validate passed
```

Your submission is ready to submit!

## Hugging Face Space

**URL:** https://huggingface.co/spaces/virustechhacks/adaptive-project-management
**Endpoint:** https://virustechhacks-adaptive-project-management.hf.space

## Notes

- The PowerShell script automatically detects whether to use `openenv` directly or via `uv run`
- Docker build timeout is set to 600 seconds (10 minutes)
- If HF Space is still building, Step 1 will fail - wait for deployment to complete first
