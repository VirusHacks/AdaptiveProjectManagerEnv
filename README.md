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

<div align="center">

# 🎯 Adaptive Project Manager

**An OpenEnv environment where AI learns to manage software projects under uncertainty.**

[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compatible-blue)](https://github.com/openenv)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-BSD--3-green.svg)](LICENSE)

[Quick Start](#-quick-start) • [Architecture](#-architecture) • [Reward System](#-reward-system) • [Tasks](#-tasks) • [API](#-api-reference)

</div>

---

## 💡 The Problem

Software projects fail for predictable reasons: critical work discovered late, overloaded teams, shifting priorities, cascading delays. Traditional tools track status—they don't help **decide what to do next**.

This environment asks: **Can an agent learn to manage a project better than fixed rules?**

> 📖 *Full problem analysis: [Problem.md](Problem.md)*

---

## 🏗️ Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│  Agent / Policy  │ ──► │  OpenEnv API     │ ──► │  Env Orchestrator    │
│  chooses action  │     │  reset / step    │     │  controls step order │
└────────┬─────────┘     └────────┬─────────┘     └──────────┬───────────┘
         │                        │                          │
         │                        ▼                          ▼
         │               ┌─────────────────┐         ┌───────────────┐
         │               │  ProjectState   │ ◄─────► │  Task Engine  │
         │               │  (truth source) │         │  dependencies │
         │               │                 │         │  effort calc  │
         │               │  • day, budget  │         └───────────────┘
         │               │  • tasks [ ]    │         ┌───────────────┐
         │               │  • employees [ ]│ ◄─────► │ Employee Eng  │
         │               │  • risks [ ]    │         │ burnout/skills│
         │               └────────┬────────┘         └───────────────┘
         │                        │                  ┌───────────────┐
         │                        └────────────────► │ Reward Engine │
         │                                           │ + Grader      │
         ▼                                           └───────────────┘
┌──────────────────┐
│ Observation Out  │ ◄── (obs, reward, done)
└──────────────────┘
```

**One step = one project day.** The orchestrator executes in deterministic order: events → assignments → work → burnout → budget → reward → termination.

> 📖 *Full system design: [Architecture.md](Architecture.md)*

---

## 🎮 Quick Start

### Prerequisites
```bash
git clone <repo-url> && cd adaptive-project-manager
uv sync  # or: pip install -e .
```

### Run Inference
```bash
cp .env.example .env  # Configure HF_TOKEN, API_BASE_URL, MODEL_NAME
uv run python inference.py
```

### Launch Interactive Dashboard
```bash
# Start the server
uv run uvicorn server.app:app --host 0.0.0.0 --port 8000

# Open in browser
# → http://localhost:8000/dashboard
```

**🎯 Mission Control Dashboard** - A NASA-inspired command center showing:
- **Live dependency graph** with critical path visualization
- **Real-time reward breakdown** (completion, critical path bonus, skill matching)
- **Team burnout meters** and skill-aware assignments
- **Event timeline** with color-coded outcomes
- **Auto-play mode** for hands-free demonstration

### Local Testing
```python
from server.hustlers_env_environment import AdaptiveProjectManagerEnv
from models import ProjectAction, Assignment

env = AdaptiveProjectManagerEnv()
obs = env.reset(task_id="easy")

while not obs.done:
    action = ProjectAction(
        assignments=[Assignment(employee_id="emp_1", task_id="task_1")],
        contingency_action="none"
    )
    obs = env.step(action)
    print(f"Day {obs.day}: {obs.project_completion:.0%} complete")
```

---

## 💰 Reward System

The reward shapes **realistic PM behavior**—not just task completion.

### Step Reward

```
R = 5·Ccrit + 2·Cnorm + 1.5·Dblocked + 0.5·U + 0.5·M − 0.25 − 3·Overdue − Pburnout − Preassign
```

| Component | Value | Purpose |
|-----------|-------|---------|
| Complete critical task | **+5.0** | Prioritize critical path |
| Complete normal task | **+2.0** | Reward progress |
| **Critical path bonus** | **+1.5 × downstream** | 🆕 Clear blockers first |
| Unblock task | **+0.5** | Create options |
| Skill match | **+0.5** | Good assignments |
| Time cost | **−0.25** | Encourage speed |
| Overdue critical | **−3.0** | Penalize delays |
| Burnout | **−(avg−0.6)×2** | Protect team |
| Reassignment | **−0.5** | Discourage thrashing |

### 🆕 Critical Path Bonus

When task X completes: `bonus = downstream_blocked(X) × 1.5`

```
Example: task_1 blocks task_3, which blocks task_5
         Complete task_1 → downstream = 2 → bonus = +3.0
```

**Teaches: clear blockers first.**

### Final Score

```
Score = 0.35·Completion + 0.25·Deadline + 0.15·Budget + 0.15·TeamHealth + 0.10·Satisfaction
```

> 📖 *Reward rationale & edge cases: [Reward_Design.md](Reward_Design.md)*

---

## 📋 Tasks

Three difficulty levels with **deterministic seeds** for reproducible evaluation:

| Task | Scenario | Team | Tasks | Days | Key Challenge |
|------|----------|------|-------|------|---------------|
| `easy` | Web Launch | 3 | 5 | 12 | Basic dependencies |
| `medium` | MVP Crunch | 4 | 9 | 18 | Illness day 6, scope change day 10 |
| `hard` | Migration | 5 | 14+ | 25 | Multiple overlapping crises |

### Expected Scores

| Policy | Easy | Medium | Hard |
|--------|------|--------|------|
| Random | 0.15–0.30 | 0.10–0.20 | 0.05–0.15 |
| Heuristic | 0.80–0.90 | 0.55–0.70 | 0.35–0.50 |
| **Strong Agent** | **0.95+** | **0.75–0.85** | **0.60–0.75** |

> 📖 *Task specs & events: [Tasks.md](Tasks.md)*

---

## 📡 API Reference

### Action

```python
class ProjectAction:
    assignments: List[Assignment]    # Who works on what
    reprioritized_tasks: List[str]  # Escalate to critical
    contingency_action: Literal[
        "none",                      # Normal
        "request_overtime",          # +20% productivity, +burnout
        "hire_contractor",           # Add capacity, $$$
        "defer_low_priority_work"    # Focus critical path
    ]
```

### Observation

```python
class ProjectObservation:
    day: int                  # Current day
    days_remaining: int       # Until deadline
    budget_remaining: float   # Dollars left
    project_completion: float # 0.0–1.0
    blocked_tasks: int        # Cannot proceed
    overdue_tasks: int        # Past deadline
    average_burnout: float    # Team health
    tasks: List[TaskState]
    employees: List[EmployeeState]
    risks: List[RiskState]
    message: str              # Recent events
    done: bool
    reward: float
```

### Task & Employee State

```python
class TaskState:
    id: str
    status: Literal["todo", "in_progress", "blocked", "done"]
    priority: Literal["low", "medium", "high", "critical"]
    required_skill: str
    remaining_effort: float
    dependencies: List[str]
    is_critical_path: bool

class EmployeeState:
    id: str
    skills: List[str]
    available: bool
    burnout: float  # 0.0–1.0, >0.8 = 50% productivity
```

> 📖 *Complete state/action design: [State_Actions.md](State_Actions.md)*

---

## ⚙️ Mechanics

### Productivity

```
productivity = Σ(skill_scores) × coordination_factor
coordination_factor = 1 / (1 + 0.15 × (n_assigned - 1))
```

| Skill Match | Score | Team Size | Output |
|-------------|-------|-----------|--------|
| Exact | 1.0 | 1 | 1.00× |
| Partial | 0.5 | 2 | 1.74× |
| None | 0.0 | 3 | 2.31× |

### Burnout

```
burnout += 0.15 × workload − 0.05 × rest
if overtime: burnout += 0.10
if burnout > 0.8: productivity × 0.5
```

---

## 🧪 Testing

```bash
uv run python -m pytest test_main.py -v          # Unit tests
uv run python test_enhancements.py               # Feature tests
```

---

## 🤖 Optional: RL Training

For researchers (not required for OpenEnv):

```bash
uv add gymnasium stable-baselines3 sb3-contrib
uv run python train_maskable_ppo.py --task easy --timesteps 100000
```

**Gym Wrapper Features:**
- Multi-Discrete: `[employee, task, contingency]`
- Action masking for MaskablePPO
- Prevents invalid actions (busy employees, blocked tasks)

---

## 🐳 Docker

```bash
docker build -t adaptive-project-manager:latest .
docker run -p 8000:8000 adaptive-project-manager:latest
openenv push --repo-id your-username/adaptive-project-manager
```

---

## 📁 Structure

```
├── models.py                    # Pydantic models
├── inference.py                 # LLM inference
├── server/
│   ├── hustlers_env_environment.py  # Core env
│   └── gym_wrapper.py           # RL wrapper
├── tasks/{easy,medium,hard}.py  # Task configs
├── graders/                     # Scoring logic
├── Architecture.md              # System design
├── Reward_Design.md             # Reward rationale
├── State_Actions.md             # API details
├── Tasks.md                     # Task specs
└── CHANGELOG.md                 # Version history
```

---

## 📊 Evaluation Alignment

| Criterion | Weight | Implementation |
|-----------|--------|----------------|
| **Real-world utility** | 30% | Models actual PM decisions |
| **Reward quality** | 25% | Dense signals, critical path bonus |
| **Task & grader** | 25% | 3 tasks, deterministic seeds |
| **Environment design** | 20% | Clean API, skill matching |

---

<div align="center">

**Built for the OpenEnv Hackathon** 🚀

[Architecture](Architecture.md) • [Rewards](Reward_Design.md) • [Tasks](Tasks.md) • [Changelog](CHANGELOG.md)

</div>
