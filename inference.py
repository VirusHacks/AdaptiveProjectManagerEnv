"""
Inference Script for Adaptive Project Manager Environment
=========================================================

MANDATORY:
- Before submitting, ensure the following variables are defined in your environment configuration:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.

STDOUT FORMAT:
    [START] task=<task_name>
    [STEP] day=<n> action={...} reward=<0.00>
    [END] task=<task_name> score=<score>
"""

import asyncio
import json
import os
import textwrap
from pathlib import Path
from typing import List, Optional, Dict, Any

from openai import OpenAI

from client import AdaptiveProjectManagerClient
from models import ProjectAction, Assignment, TaskState, EmployeeState


def load_local_env_file(path: str = ".env") -> None:
    env_path = Path(__file__).resolve().parent / path
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


load_local_env_file()

IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("IMAGE_NAME") or "adaptive-project-manager:latest"
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")

API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

TASKS = ["easy", "medium", "hard"]
MAX_STEPS = 50  # Maximum steps per task
TEMPERATURE = 0.3
MAX_TOKENS = 500

SYSTEM_PROMPT = textwrap.dedent("""
    You are a project manager AI for a software development project.
    Your goal is to complete all tasks before the deadline while keeping the team healthy.
    
    You must respond with a valid JSON action with this structure:
    {
        "assignments": [{"employee_id": "emp_X", "task_id": "task_Y"}, ...],
        "reprioritized_tasks": [],
        "contingency_action": "none"
    }
    
    Rules:
    1. Assign employees to tasks matching their skills for best productivity
    2. Don't assign unavailable employees
    3. Don't assign to tasks with unmet dependencies (blocked tasks)
    4. Use contingency_action wisely:
       - "request_overtime": increases productivity but causes burnout
       - "hire_contractor": adds a versatile employee but costs more
       - "defer_low_priority_work": blocks low priority tasks to focus on critical ones
       - "none": no special action
    5. Watch burnout levels - employees with burnout > 0.8 work at 50% capacity
    6. Prioritize critical path tasks
    
    Reply ONLY with the JSON action, no other text.
""").strip()


def log_start(task: str) -> None:
    print(f"[START] task={task}", flush=True)


def log_step(day: int, action: Dict, reward: float) -> None:
    action_str = json.dumps(action, separators=(',', ':'))
    print(f"[STEP] day={day} action={action_str} reward={reward:.2f}", flush=True)


def log_end(task: str, score: float) -> None:
    print(f"[END] task={task} score={score:.2f}", flush=True)


def build_user_prompt(
    day: int,
    days_remaining: int,
    budget_remaining: float,
    project_completion: float,
    average_burnout: float,
    tasks: List[TaskState],
    employees: List[EmployeeState],
    message: str,
) -> str:
    """Build the user prompt with current state."""
    
    # Format tasks
    task_lines = []
    for t in tasks:
        status_emoji = {"todo": "⬜", "in_progress": "🔄", "blocked": "🚫", "done": "✅"}.get(t.status, "?")
        deps = f" (depends on: {', '.join(t.dependencies)})" if t.dependencies else ""
        assigned = f" [assigned: {', '.join(t.assigned_employees)}]" if t.assigned_employees else ""
        task_lines.append(
            f"  {status_emoji} {t.id}: {t.name} | priority={t.priority} | skill={t.required_skill} | "
            f"effort_remaining={t.remaining_effort:.1f} | critical_path={t.is_critical_path}{deps}{assigned}"
        )
    
    # Format employees
    emp_lines = []
    for e in employees:
        avail = "✅" if e.available else "❌"
        assigned = f" -> {e.assigned_task_id}" if e.assigned_task_id else " -> unassigned"
        emp_lines.append(
            f"  {avail} {e.id} ({e.name}): skills={e.skills} | burnout={e.burnout:.2f} | workload={e.workload:.1f}{assigned}"
        )
    
    return textwrap.dedent(f"""
        === Day {day} / {day + days_remaining} ===
        Days remaining: {days_remaining}
        Budget remaining: ${budget_remaining:,.0f}
        Project completion: {project_completion*100:.1f}%
        Average team burnout: {average_burnout:.2f}
        
        Recent events: {message}
        
        TASKS:
        {chr(10).join(task_lines)}
        
        EMPLOYEES:
        {chr(10).join(emp_lines)}
        
        Decide your action for today. Reply with JSON only.
    """).strip()


def parse_action_response(response: str) -> Optional[ProjectAction]:
    """Parse LLM response into a ProjectAction."""
    try:
        # Clean up response - find JSON object
        response = response.strip()
        
        # Try to find JSON in the response
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            return None
        
        json_str = response[start_idx:end_idx + 1]
        data = json.loads(json_str)
        
        assignments = [
            Assignment(employee_id=a["employee_id"], task_id=a["task_id"])
            for a in data.get("assignments", [])
        ]
        
        return ProjectAction(
            assignments=assignments,
            reprioritized_tasks=data.get("reprioritized_tasks", []),
            contingency_action=data.get("contingency_action", "none"),
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def get_heuristic_action(
    tasks: List[TaskState],
    employees: List[EmployeeState],
    day: int,
    days_remaining: int,
    average_burnout: float,
) -> ProjectAction:
    """
    Fallback heuristic policy.
    
    Strategy:
    - Pick highest-priority unblocked task
    - Assign best matching available employee
    - Use contingency actions if behind schedule
    """
    assignments = []
    
    # Sort tasks by priority (critical > high > medium > low) and critical path
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    
    available_tasks = [
        t for t in tasks 
        if t.status in ["todo", "in_progress"] 
        and t.status != "blocked"
    ]
    available_tasks.sort(key=lambda t: (
        priority_order.get(t.priority, 4),
        not t.is_critical_path,
        t.remaining_effort
    ))
    
    # Get available employees not assigned yet
    available_employees = [e for e in employees if e.available and e.assigned_task_id is None]
    
    # Assign employees to tasks
    for task in available_tasks:
        if not available_employees:
            break
        
        # Find best matching employee
        best_emp = None
        best_score = -1
        
        for emp in available_employees:
            score = 0
            if task.required_skill in emp.skills:
                score = 10  # Exact skill match
            elif any(s in task.required_skill for s in emp.skills):
                score = 5  # Partial match
            
            # Prefer less burned out employees
            score -= emp.burnout * 5
            
            if score > best_score:
                best_score = score
                best_emp = emp
        
        if best_emp and best_score >= 0:
            assignments.append(Assignment(
                employee_id=best_emp.id,
                task_id=task.id
            ))
            available_employees.remove(best_emp)
    
    # Determine contingency action
    contingency = "none"
    
    # Calculate progress
    critical_tasks = [t for t in tasks if t.is_critical_path]
    critical_done = sum(1 for t in critical_tasks if t.status == "done")
    critical_total = len(critical_tasks)
    
    expected_progress = day / (day + days_remaining) if days_remaining > 0 else 1.0
    actual_progress = critical_done / critical_total if critical_total > 0 else 1.0
    
    if actual_progress < expected_progress - 0.2:
        # We're behind schedule
        if average_burnout < 0.5:
            contingency = "request_overtime"
        elif len(employees) < 5:
            contingency = "hire_contractor"
        else:
            contingency = "defer_low_priority_work"
    
    return ProjectAction(
        assignments=assignments,
        reprioritized_tasks=[],
        contingency_action=contingency,
    )


def get_model_action(
    client: OpenAI,
    day: int,
    days_remaining: int,
    budget_remaining: float,
    project_completion: float,
    average_burnout: float,
    tasks: List[TaskState],
    employees: List[EmployeeState],
    message: str,
) -> ProjectAction:
    """Get action from LLM or fall back to heuristic."""
    
    user_prompt = build_user_prompt(
        day=day,
        days_remaining=days_remaining,
        budget_remaining=budget_remaining,
        project_completion=project_completion,
        average_burnout=average_burnout,
        tasks=tasks,
        employees=employees,
        message=message,
    )
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        response = (completion.choices[0].message.content or "").strip()
        
        action = parse_action_response(response)
        if action:
            return action
        
    except Exception:
        pass
    
    # Fallback to heuristic
    return get_heuristic_action(
        tasks=tasks,
        employees=employees,
        day=day,
        days_remaining=days_remaining,
        average_burnout=average_burnout,
    )


async def run_task(client: OpenAI, env, task_id: str) -> float:
    """Run a single task and return the final score."""
    
    log_start(task=task_id)
    
    rewards: List[float] = []
    final_score = 0.0
    
    try:
        result = await env.reset(task_id=task_id)
        obs = result.observation
        
        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break
            
            # Get action from LLM or heuristic
            action = get_model_action(
                client=client,
                day=obs.day,
                days_remaining=obs.days_remaining,
                budget_remaining=obs.budget_remaining,
                project_completion=obs.project_completion,
                average_burnout=obs.average_burnout,
                tasks=obs.tasks,
                employees=obs.employees,
                message=obs.message,
            )
            
            # Execute action
            result = await env.step(action)
            obs = result.observation
            reward = result.reward or 0.0
            
            rewards.append(reward)
            
            # Log step
            action_dict = {
                "assignments": [{"e": a.employee_id, "t": a.task_id} for a in action.assignments],
                "contingency": action.contingency_action,
            }
            log_step(day=obs.day, action=action_dict, reward=reward)
            
            if result.done:
                # Get final score from metadata
                final_score = obs.metadata.get("final_score", 0.0)
                break
        
        # If we reached max steps without done, compute score from rewards
        if not result.done:
            final_score = max(0.0, min(1.0, sum(rewards) / len(rewards) + 0.5)) if rewards else 0.0
        
    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        final_score = 0.0
    
    log_end(task=task_id, score=final_score)
    return final_score


async def main() -> None:
    """Main inference loop over all tasks."""
    
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    env = await AdaptiveProjectManagerClient.from_docker_image(IMAGE_NAME)
    
    scores = {}
    
    try:
        for task_id in TASKS:
            score = await run_task(client, env, task_id)
            scores[task_id] = score
    
    finally:
        try:
            await env.close()
        except Exception:
            pass
    
    # Summary
    avg_score = sum(scores.values()) / len(scores) if scores else 0.0
    print(f"[SUMMARY] average_score={avg_score:.2f}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())