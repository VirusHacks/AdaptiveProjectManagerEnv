# State and Action Space Design for `AdaptiveProjectManagerEnv`

This document defines what the agent can **observe** and what it can **do** at each step.
The state/action design is compact, interpretable, and expressive enough to model realistic project-management decisions.

## At a Glance

- Observation space captures project health, team state, task state, and active risks.
- Action space supports assignment, reprioritization, and strategic contingency actions.
- Task progress is continuous via remaining effort, which enables long-running work.
- Design prioritizes reproducibility, readability, and OpenEnv compatibility.

## Design Principles

The state and action spaces are designed to be:

- small enough for efficient model context usage,
- rich enough for meaningful decision-making,
- interpretable by humans,
- easy to serialize and validate through OpenEnv.

The intent is not to model every real-world detail. The intent is to include the minimum information needed for strong sequential decisions.

---

## Observation Space

At each step, the agent receives a structured observation that answers:

> What is the current state of the project?

The observation has four components:

1. Global project state
2. Employee state
3. Task state
4. Active risk state

### Global Project State

```python
class Observation(BaseModel):
    day: int
    days_remaining: int
    budget_remaining: float
    project_completion: float
    blocked_tasks: int
    overdue_tasks: int
    average_burnout: float
```

| Field | Meaning |
| --- | --- |
| `day` | Current simulated day |
| `days_remaining` | Remaining days before deadline |
| `budget_remaining` | Remaining available budget |
| `project_completion` | Fraction of total effort completed |
| `blocked_tasks` | Number of tasks that cannot start yet |
| `overdue_tasks` | Number of critical tasks currently late |
| `average_burnout` | Mean burnout across employees |

These fields give the agent a compact view of urgency, schedule pressure, and overall project health.

### Employee State

```python
class EmployeeState(BaseModel):
    id: str
    skills: list[str]
    available: bool
    assigned_task_id: Optional[str]
    workload: float
    burnout: float
```

| Field | Meaning |
| --- | --- |
| `id` | Unique employee identifier |
| `skills` | Skills the employee can contribute |
| `available` | Whether the employee can currently work |
| `assigned_task_id` | Current task assignment (if any) |
| `workload` | Current workload in $[0,1]$ |
| `burnout` | Current burnout in $[0,1]$ |

`workload` and `burnout` are critical because they create delayed effects.

Example:

- Reusing the same employee repeatedly can improve short-term throughput,
- but increases burnout risk and can reduce long-run score.

### Task State

```python
class TaskState(BaseModel):
    id: str
    priority: Literal["low", "medium", "high", "critical"]
    status: Literal["todo", "in_progress", "blocked", "done"]
    required_skill: str
    remaining_effort: float
    dependencies: list[str]
    is_critical_path: bool
```

| Field | Meaning |
| --- | --- |
| `id` | Unique task identifier |
| `priority` | Business importance |
| `status` | Current task status |
| `required_skill` | Skill needed for efficient completion |
| `remaining_effort` | Work remaining (in day-equivalent effort units) |
| `dependencies` | Upstream tasks that must complete first |
| `is_critical_path` | Whether delay directly affects deadline |

`remaining_effort` makes long-running tasks explicit, which is essential for planning depth.

### Risk State

```python
class RiskState(BaseModel):
    type: str
    severity: float
    days_remaining: int
```

Typical risk types:

- employee absence,
- vendor delay,
- urgent requirement,
- burnout escalation.

Risk state allows proactive decisions instead of purely reactive ones.

---

## Modeling Long-Running Tasks

Tasks are not completed in one step. Each task tracks effort over time.

Let $E_t$ be remaining effort at day $t$:

$$
E_t = \text{remaining effort at day } t
$$

Daily update rule:

$$
E_{t+1} = \max(0, E_t - P_t)
$$

where $P_t$ is total productivity applied to that task on day $t$.

### Productivity Formula

For a single assigned employee:

$$
P_t = s
$$

where:

- $s = 1.0$ for a strong skill match,
- $s = 0.5$ for a partial match.

For $n$ assigned employees:

$$
P_t = \left(\sum_{i=1}^{n} s_i\right) \cdot c(n)
$$

with coordination factor:

$$
c(n) = \frac{1}{1 + 0.15(n-1)}
$$

This models diminishing returns from coordination overhead.

| Employees Assigned | Effective Productivity |
| --- | --- |
| 1 | 1.00 |
| 2 | 1.74 |
| 3 | 2.31 |

This creates a key planning decision:

> Concentrate people on one blocker, or distribute them across multiple tasks?

---

## Action Space

At each step, the agent chooses an action that answers:

> What should the project manager do today?

```python
class Action(BaseModel):
    assignments: list[Assignment]
    reprioritized_tasks: list[str]
    contingency_action: Literal[
        "none",
        "request_overtime",
        "hire_contractor",
        "defer_low_priority_work"
    ]
```
```

### Assignment Actions

```python
class Assignment(BaseModel):
    employee_id: str
    task_id: str
```

The agent may:

- assign one employee to one task,
- assign multiple employees to one task,
- leave some employees idle.

Important constraints and side effects:

- idle employees are penalized when useful work exists,
- unnecessary switching is penalized,
- sustained overload increases burnout.

### Reprioritization Actions

The agent can temporarily elevate one or more tasks in `reprioritized_tasks`.

This is most useful when:

- a disruption occurs,
- a critical task is blocked,
- deadline pressure increases suddenly.

Reprioritization changes scheduling preference in baseline heuristics and downstream execution logic.

### Contingency Actions

Contingency actions model strategic interventions with delayed consequences.

| Action | Primary Effect |
| --- | --- |
| `none` | Continue normal execution |
| `request_overtime` | Increase short-term productivity; increase burnout risk |
| `hire_contractor` | Add temporary capacity; reduce budget |
| `defer_low_priority_work` | Reduce optional scope pressure; may lower stakeholder satisfaction |

These are high-impact choices and often dominate long-term return.

---

## Why This State/Action Design Works

This design is effective because it is:

- compact enough for fast evaluation,
- expressive enough for long-horizon planning,
- grounded in realistic delivery tradeoffs,
- deterministic and reproducible for fair benchmarking,
- easy to validate via structured schemas.

Most importantly, it creates the core RL property:

> the best action depends on future consequences, not only immediate reward.
