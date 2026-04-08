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
    Your goal is to maximize the final project score by completing tasks before the deadline
    while managing budget, team health, and stakeholder satisfaction.

    You must respond with a valid JSON action with this structure:
    {
        "assignments": [{"employee_id": "emp_X", "task_id": "task_Y"}, ...],
        "reprioritized_tasks": [],
        "contingency_action": "none"
    }

    STRATEGY GUIDELINES:
    1. DEPENDENCY CHAINS: Always check task dependencies. Prioritize tasks that unblock
       the most downstream work. Completing a blocker is worth more than completing a leaf task.
    2. SKILL MATCHING: Assign employees whose skills exactly match the task's required_skill.
       Exact match = 1.0 productivity, partial = 0.5, mismatch = 0.0.
    3. CRITICAL PATH: Tasks marked is_critical_path=true determine the deadline. Focus on these.
    4. BURNOUT MANAGEMENT: Employees with burnout > 0.8 work at 50% capacity.
       Rotate employees or leave some idle to recover. Burnout above 0.6 triggers penalties.
    5. CONTINGENCY TIMING:
       - "request_overtime": Use ONLY when behind schedule AND average burnout < 0.5
       - "hire_contractor": Use early if team is small and many tasks remain
       - "defer_low_priority_work": Use when deadline is tight to focus on critical path
       - "none": Default. Don't waste contingency actions when not needed.
    6. LONG-TERM THINKING: Overtime today causes burnout tomorrow. A burned-out team on day 15
       is worse than a slightly delayed team on day 8.
    7. Don't assign unavailable employees. Don't assign to blocked or done tasks.

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
    - Prioritize tasks that unblock the most downstream work
    - Assign best skill-matching available employee
    - Also reassign idle employees sitting on tasks that have other workers
    - Use contingency actions strategically based on schedule gap
    """
    assignments = []
    assigned_emp_ids = set()
    
    # Build a map of how many downstream tasks each task unblocks
    task_map = {t.id: t for t in tasks}
    downstream_count = {}
    for t in tasks:
        count = 0
        for other in tasks:
            if t.id in other.dependencies and other.status != "done":
                count += 1
        downstream_count[t.id] = count
    
    # Sort tasks: critical path first, then by downstream unlock value, then priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    
    # Filter to workable tasks (not done, not blocked)
    available_tasks = []
    for t in tasks:
        if t.status in ["done", "blocked"]:
            continue
        # Check if dependencies are met
        deps_met = all(
            task_map.get(dep_id) and task_map[dep_id].status == "done"
            for dep_id in t.dependencies
        )
        if deps_met or t.status == "in_progress":
            available_tasks.append(t)
    
    available_tasks.sort(key=lambda t: (
        priority_order.get(t.priority, 4),
        not t.is_critical_path,
        -downstream_count.get(t.id, 0),  # More downstream = higher priority
        t.remaining_effort
    ))
    
    # Get available employees: unassigned first, then those on lower-priority work
    unassigned_employees = [
        e for e in employees
        if e.available and e.assigned_task_id is None
    ]
    
    # Also consider employees currently on low-priority tasks that could be reassigned
    # to higher-priority work (only if their current task has other workers or is low priority)
    reassignable_employees = []
    for e in employees:
        if not e.available or e.assigned_task_id is None:
            continue
        current_task = task_map.get(e.assigned_task_id)
        if current_task and current_task.priority in ["low", "medium"] and current_task.status == "in_progress":
            # Only reassign if there's higher-priority work needing their skill
            has_better_work = any(
                t.required_skill in e.skills
                and priority_order.get(t.priority, 4) < priority_order.get(current_task.priority, 4)
                for t in available_tasks
                if t.id != e.assigned_task_id
            )
            if has_better_work:
                reassignable_employees.append(e)
    
    all_available = unassigned_employees + reassignable_employees
    
    # Assign employees to tasks
    for task in available_tasks:
        if not all_available:
            break
        
        # Find best matching employee
        best_emp = None
        best_score = -1
        
        for emp in all_available:
            if emp.id in assigned_emp_ids:
                continue
            score = 0
            if task.required_skill in emp.skills:
                score = 10  # Exact skill match
            elif any(s in task.required_skill for s in emp.skills):
                score = 5  # Partial match
            
            # Prefer less burned out employees
            score -= emp.burnout * 5
            
            # Bonus for unblocking downstream tasks
            score += downstream_count.get(task.id, 0) * 2
            
            if score > best_score:
                best_score = score
                best_emp = emp
        
        if best_emp and best_score >= 0:
            assignments.append(Assignment(
                employee_id=best_emp.id,
                task_id=task.id
            ))
            assigned_emp_ids.add(best_emp.id)
    
    # Determine contingency action
    contingency = "none"
    
    # Calculate schedule gap
    critical_tasks = [t for t in tasks if t.is_critical_path]
    critical_done = sum(1 for t in critical_tasks if t.status == "done")
    critical_total = len(critical_tasks)
    
    expected_progress = day / (day + days_remaining) if days_remaining > 0 else 1.0
    actual_progress = critical_done / critical_total if critical_total > 0 else 1.0
    
    if actual_progress < expected_progress - 0.2:
        # Behind schedule
        if average_burnout < 0.4:  # Stricter threshold than before
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
                # Get final score - try direct field first, then metadata fallback
                final_score = obs.final_score if obs.final_score is not None else obs.metadata.get("final_score", 0.0)
                break
        
        # If we reached max steps without done, compute score from rewards
        if not result.done:
            final_score = max(0.0, min(1.0, sum(rewards) / len(rewards) + 0.5)) if rewards else 0.0
        
    except Exception as e:
        print(f"[ERROR] {e}", flush=True)
        final_score = 0.0
    
    # Generate CEO Post-Mortem Email
    if 'obs' in locals() and obs is not None:
        burnout = obs.average_burnout
        budget = obs.budget_remaining
        completion = obs.project_completion
        
        email_body = ""
        if completion >= 0.99 and burnout < 0.5 and budget > 0:
            email_body = "Brilliant work. You delivered the project, kept the team sane, and stayed under budget. I'm promoting you."
        elif completion >= 0.99 and burnout >= 0.8:
            email_body = "The product shipped, but half the engineering team just quit because of 90% burnout. We cannot sustain this management style."
        elif completion < 0.5:
            email_body = "Utter failure. You barely finished half the project. We are losing the client."
        elif budget < 0:
            email_body = "You delivered it, but you completely blew past the budget. Finance is furious."
        else:
            email_body = "The project finished with acceptable margins, but there's room for improvement in your resource allocation."
            
        print("\n=== ✉️ NEW MESSAGE FROM CEO ===")
        print(email_body)
        print("===============================\n", flush=True)

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