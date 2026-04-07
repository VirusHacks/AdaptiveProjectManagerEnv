---
title: Adaptive Project Manager Environment
emoji: 📊
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - rl
  - project-management
---

# Adaptive Project Manager Environment

An OpenEnv-compatible reinforcement learning environment that simulates software project management under uncertainty. Agents must manage employees, assign tasks, handle unexpected events, and deliver projects on time while maintaining team health.

## Overview

The environment simulates one project day per step. The agent receives observations about the project state and must make decisions about:
- **Task assignments**: Which employees work on which tasks
- **Resource management**: When to use overtime, hire contractors, or defer work
- **Crisis response**: Handling unexpected events like employee illness or scope changes

## Tasks

Three difficulty levels with deterministic task configurations:

| Task | Employees | Tasks | Days | Key Challenges |
|------|-----------|-------|------|----------------|
| `easy` | 3 | 5 | 12 | Basic project, no surprises |
| `medium` | 4 | 9 | 18 | Employee illness on day 6, scope change on day 10 |
| `hard` | 5 | 14+ | 25 | Multiple crises: illness, new compliance task, vendor delays, burnout effects |

## Local Setup

Copy `.env.example` to `.env` and configure:

```text
HF_TOKEN=your_hugging_face_token_here
API_BASE_URL=https://router.huggingface.co/v1
MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
LOCAL_IMAGE_NAME=adaptive-project-manager:latest
```

## Quick Start

```python
from client import AdaptiveProjectManagerClient
from models import ProjectAction, Assignment

# Create environment from Docker image
env = await AdaptiveProjectManagerClient.from_docker_image("adaptive-project-manager:latest")

try:
    # Reset with a task
    result = await env.reset(task_id="easy")
    obs = result.observation
    print(f"Day {obs.day}: {len(obs.tasks)} tasks, {len(obs.employees)} employees")

    # Run episode
    while not result.done:
        # Create action: assign employees to tasks
        action = ProjectAction(
            assignments=[
                Assignment(employee_id="emp_1", task_id="task_1"),
                Assignment(employee_id="emp_2", task_id="task_2"),
            ],
            contingency_action="none"  # or "request_overtime", "hire_contractor", "defer_low_priority_work"
        )
        
        result = await env.step(action)
        obs = result.observation
        print(f"Day {obs.day}: Completion={obs.project_completion:.1%}, Burnout={obs.average_burnout:.2f}")

finally:
    await env.close()
```

## Environment API

### Action Space

```python
class ProjectAction:
    assignments: List[Assignment]           # Employee-to-task assignments
    reprioritized_tasks: List[str]         # Tasks to mark as critical
    contingency_action: Literal[
        "none",
        "request_overtime",        # +20% productivity, increases burnout
        "hire_contractor",         # Adds versatile employee, costs more
        "defer_low_priority_work"  # Blocks low-priority tasks
    ]
```

### Observation Space

```python
class ProjectObservation:
    day: int                    # Current project day
    days_remaining: int         # Days until deadline
    budget_remaining: float     # Remaining budget
    project_completion: float   # Overall completion (0-1)
    blocked_tasks: int          # Number of blocked tasks
    overdue_tasks: int          # Number of overdue tasks
    average_burnout: float      # Team burnout level (0-1)
    tasks: List[TaskState]      # All task details
    employees: List[EmployeeState]  # All employee details
    risks: List[RiskState]      # Active risks
    message: str                # Recent events description
```

### Task State

```python
class TaskState:
    id: str
    priority: Literal["low", "medium", "high", "critical"]
    status: Literal["todo", "in_progress", "blocked", "done"]
    required_skill: str
    remaining_effort: float
    dependencies: List[str]
    is_critical_path: bool
    assigned_employees: List[str]
```

### Employee State

```python
class EmployeeState:
    id: str
    skills: List[str]
    available: bool
    assigned_task_id: Optional[str]
    workload: float   # 0-1
    burnout: float    # 0-1, >0.8 causes 50% productivity
```

## Mechanics

### Productivity Calculation

```python
productivity = sum(skill_match_scores) * coordination_factor

# Skill matching
exact_match = 1.0
partial_match = 0.5
no_match = 0.0

# Coordination penalty for multiple employees on same task
coordination_factor = 1 / (1 + 0.15 * (n_assigned - 1))
```

### Burnout System

```python
# Daily update
burnout += 0.15 * workload - 0.05 * recovery

# Overtime increases burnout by additional 0.1
# Burnout > 0.8 reduces productivity to 50%
```

### Reward Function

```python
step_reward = (
    5 * newly_completed_critical_tasks
    + 2 * newly_completed_normal_tasks
    + 1 * newly_unblocked_tasks
    + 0.5 * skill_match_count
    - 0.25                          # Base cost per step
    - 3 * overdue_critical_tasks
    - burnout_penalty
    - reassignment_penalty
)
```

### Final Score

```python
final_score = (
    0.35 * completion_score        # Weighted by task priority
    + 0.25 * deadline_score        # Bonus for early, penalty for late
    + 0.15 * budget_score          # Remaining budget
    + 0.15 * team_health_score     # Inverse of burnout
    + 0.10 * stakeholder_satisfaction
)
# Clamped to [0.0, 1.0]
```

## Building the Docker Image

```bash
docker build -t adaptive-project-manager:latest .
docker run -p 8000:8000 adaptive-project-manager:latest
```

## Running Inference

```bash
python inference.py
```

Output format:
```
[START] task=easy
[STEP] day=2 action={"assignments":[{"e":"emp_1","t":"task_1"}],"contingency":"none"} reward=0.50
[END] task=easy score=0.85
```

## Project Structure

```
adaptive-project-manager/
├── models.py              # Pydantic models (Action, Observation, State)
├── client.py              # Environment client
├── inference.py           # LLM inference script
├── openenv.yaml           # OpenEnv configuration
├── pyproject.toml         # Dependencies
├── Dockerfile             # Container definition
├── server/
│   ├── app.py             # FastAPI application
│   └── hustlers_env_environment.py  # Core environment logic
├── tasks/
│   ├── easy.py            # Easy task configuration
│   ├── medium.py          # Medium task configuration
│   └── hard.py            # Hard task configuration
└── graders/
    ├── base_grader.py     # Shared grading logic
    ├── easy_grader.py     # Easy task grader
    ├── medium_grader.py   # Medium task grader
    └── hard_grader.py     # Hard task grader
```

## Testing

```bash
uv run python -m pytest test_main.py -v
```

## Deployment

```bash
openenv push --repo-id your-username/adaptive-project-manager
```
