# Debug Scripts

This folder contains diagnostic and testing scripts used during development and debugging.

## Scripts

### `debug_score.py`
Focused debugging script to trace the final_score transmission issue.
- Tests metadata propagation through the environment
- Verifies observation serialization
- Checks final_score in both metadata and direct field
- **Usage**: `uv run python debug_scripts/debug_score.py`

### `quick_test.py`
Quick verification script for testing Docker builds and final_score fixes.
- Starts a fresh container from the latest image
- Runs a simple episode to completion
- Verifies final_score is properly transmitted
- **Usage**: `uv run python debug_scripts/quick_test.py`

## Purpose

These scripts were created to:
1. Diagnose the bug where `final_score` was always 0.00
2. Trace the root cause (OpenEnv's serialization excluding metadata)
3. Verify the fix (adding `final_score` as a direct field on ProjectObservation)
4. Ensure the Docker build and deployment work correctly

## Fix Summary

The final_score bug was fixed by:
- Adding `final_score: Optional[float]` to `ProjectObservation` in `models.py`
- Populating it in `server/hustlers_env_environment.py`
- Reading it in `client.py` and `inference.py`

This bypasses OpenEnv's metadata exclusion in serialization.
