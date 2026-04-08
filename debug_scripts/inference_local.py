"""
Local Inference Script (No Docker Required)
==========================================

Runs inference directly on the local environment without Docker.
Useful for testing and development.
"""

import os
import json
from pathlib import Path
from typing import List

# Set defaults for testing
os.environ.setdefault("API_BASE_URL", "https://router.huggingface.co/v1")
os.environ.setdefault("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
os.environ.setdefault("HF_TOKEN", "test_token")

try:
    from openai import OpenAI
    USE_LLM = True
except ImportError:
    USE_LLM = False
    print("OpenAI not installed - using heuristic only")

from server.hustlers_env_environment import AdaptiveProjectManagerEnv
from models import ProjectAction, Assignment


TASKS = ["easy", "medium", "hard"]
MAX_STEPS = 50
TEMPERATURE = 0.3
MAX_TOKENS = 500

API_BASE_URL = os.getenv("API_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")


def log_start(task: str) -> None:
    print(f"[START] task={task}", flush=True)


def log_step(day: int, action: dict, reward: float) -> None:
    action_str = json.dumps(action, separators=(',', ':'))
    print(f"[STEP] day={day} action={action_str} reward={reward:.2f}", flush=True)


def log_end(task: str, score: float) -> None:
    print(f"[END] task={task} score={score:.2f}", flush=True)


def get_heuristic_action(env_obs):
    """Simple heuristic policy."""
    assignments = []
    
    # Get available employees and tasks
    available_emps = [e for e in env_obs.employees if e.available and e.assigned_task_id is None]
    available_tasks = [t for t in env_obs.tasks if t.status in ["todo", "in_progress"]]
    
    # Assign employees to tasks based on skill match
    for emp in available_emps:
        for task in available_tasks:
            # Check dependencies
            deps_met = all(
                any(t.id == dep and t.status == "done" for t in env_obs.tasks)
                for dep in task.dependencies
            )
            if not deps_met:
                continue
            
            # Check skill match
            if task.required_skill in emp.skills:
                assignments.append(Assignment(employee_id=emp.id, task_id=task.id))
                available_tasks.remove(task)
                break
    
    # Determine contingency
    contingency = "none"
    critical_tasks = [t for t in env_obs.tasks if t.is_critical_path]
    critical_done = sum(1 for t in critical_tasks if t.status == "done")
    critical_total = len(critical_tasks)
    
    if critical_total > 0:
        expected_progress = env_obs.day / (env_obs.day + env_obs.days_remaining) if env_obs.days_remaining > 0 else 1.0
        actual_progress = critical_done / critical_total
        
        if actual_progress < expected_progress - 0.2:
            if env_obs.average_burnout < 0.5:
                contingency = "request_overtime"
            elif len(env_obs.employees) < 5:
                contingency = "hire_contractor"
    
    return ProjectAction(
        assignments=assignments,
        reprioritized_tasks=[],
        contingency_action=contingency,
    )


def run_task(task_id: str) -> float:
    """Run a single task and return the final score."""
    
    log_start(task=task_id)
    
    env = AdaptiveProjectManagerEnv()
    obs = env.reset(task_id=task_id)
    
    rewards: List[float] = []
    final_score = 0.0
    
    try:
        for step in range(1, MAX_STEPS + 1):
            if obs.done:
                break
            
            # Get action (heuristic only for now)
            action = get_heuristic_action(obs)
            
            # Execute action
            obs = env.step(action)
            reward = obs.reward or 0.0
            
            rewards.append(reward)
            
            # Log step
            action_dict = {
                "assignments": [{"e": a.employee_id, "t": a.task_id} for a in action.assignments],
                "contingency": action.contingency_action,
            }
            log_step(day=obs.day, action=action_dict, reward=reward)
            
            if obs.done:
                # Get final score from metadata
                final_score = obs.metadata.get("final_score", 0.0)
                break
        
        # If we reached max steps without done, compute score
        if not obs.done:
            from graders import GRADER_REGISTRY
            state = env.get_project_state()
            final_score = GRADER_REGISTRY[task_id](state)
    
    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        final_score = 0.0
    
    log_end(task=task_id, score=final_score)
    return final_score


def main() -> None:
    """Main inference loop over all tasks."""
    
    print(f"Running local inference (no Docker)", flush=True)
    print(f"Using heuristic policy", flush=True)
    print("=" * 60, flush=True)
    
    scores = {}
    
    for task_id in TASKS:
        score = run_task(task_id)
        scores[task_id] = score
    
    # Summary
    avg_score = sum(scores.values()) / len(scores) if scores else 0.0
    print("=" * 60, flush=True)
    print(f"[SUMMARY] average_score={avg_score:.2f}", flush=True)
    for task_id, score in scores.items():
        print(f"  {task_id}: {score:.2f}", flush=True)


if __name__ == "__main__":
    main()
