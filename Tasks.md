# Task Design for `AdaptiveProjectManagerEnv`

This document defines the three benchmark tasks used to evaluate agents in `AdaptiveProjectManagerEnv`.
The tasks are intentionally progressive: each level adds a new planning challenge instead of only increasing size.

## At a Glance

| Difficulty | Scenario | Main Skill Tested |
| --- | --- | --- |
| Easy | `small_web_launch` | Basic assignment and dependency handling |
| Medium | `startup_mvp_crunch` | Tradeoff reasoning under moderate uncertainty |
| Hard | `enterprise_migration_crisis` | Long-horizon planning under interacting disruptions |

Expected policy ordering is:

- random policy performs poorly,
- simple heuristic performs reasonably,
- planning-based agent performs best.

---

## Common Structure Across All Tasks

Each task includes:

- a fixed project graph,
- a team with diverse skills,
- a deadline and budget,
- deterministic stochastic events controlled by seed,
- a final normalized score in $[0,1]$.

An episode ends when one of the following occurs:

- all required work is completed,
- max day limit is reached,
- budget is exhausted (project failure).

---

## Easy Task — `small_web_launch`

### Objective

Deliver a small product website before the deadline.

### Why This Task Exists

This task verifies foundational behavior:

- correct employee-to-task assignment,
- dependency-aware scheduling,
- focus on critical work before low-value tasks.

It contains no major disruptions, so a strong heuristic baseline should perform well.

### Configuration

| Property | Value |
| --- | --- |
| Employees | 3 |
| Tasks | 5 |
| Deadline | 12 days |
| Budget | 100 units |
| Max Episode Length | 12 steps |
| Random Seed | 42 |

### Team

| Employee | Skills |
| --- | --- |
| `dev_backend` | backend |
| `dev_frontend` | frontend |
| `qa_engineer` | testing |

### Task List

| Task ID | Description | Skill | Duration | Depends On | Priority |
| --- | --- | --- | --- | --- | --- |
| T1 | Build landing page | frontend | 2 days | None | Medium |
| T2 | Build login API | backend | 3 days | None | High |
| T3 | Connect frontend to API | frontend | 2 days | T1, T2 | High |
| T4 | Run integration testing | testing | 2 days | T3 | High |
| T5 | Write documentation | frontend | 1 day | None | Low |

### Key Reasoning Challenge

- T3 is blocked until both T1 and T2 complete.
- Starting with T5 is suboptimal because it does not advance the critical path.
- Strong behavior starts T1 and T2 early to unblock downstream tasks.

### Expected Performance

| Policy | Expected Score |
| --- | --- |
| Random | 0.15–0.30 |
| Heuristic Baseline | 0.80–0.90 |
| Strong Agent | 0.95+ |

---

## Medium Task — `startup_mvp_crunch`

### Objective

Ship a startup MVP under moderate time pressure while handling fixed disruptions.

### Why This Task Exists

This task introduces real tradeoffs:

- long-running tasks,
- burnout risk,
- budget pressure,
- deterministic disruptions.

Short-term greedy choices begin to fail at this level.

### Configuration

| Property | Value |
| --- | --- |
| Employees | 4 |
| Tasks | 9 |
| Deadline | 18 days |
| Budget | 160 units |
| Max Episode Length | 18 steps |
| Random Seed | 1337 |

### Team

| Employee | Skills |
| --- | --- |
| `backend_lead` | backend |
| `frontend_dev` | frontend |
| `qa_engineer` | testing |
| `product_designer` | design |

### Task Characteristics

| Task Type | Example | Duration |
| --- | --- | --- |
| Short | Create login screen | 1–2 days |
| Medium | Implement API service | 3–4 days |
| Long-running | Build payment system | 6 days |

Long-running tasks create delayed consequences. If they start too late, deadline recovery becomes impossible.

### Example Task Graph

| Task ID | Description | Duration | Priority |
| --- | --- | --- | --- |
| T1 | Product wireframes | 2 | Medium |
| T2 | Authentication API | 3 | High |
| T3 | Frontend login flow | 2 | High |
| T4 | Payment integration | 6 | Critical |
| T5 | Database setup | 3 | High |
| T6 | Dashboard page | 2 | Medium |
| T7 | Integration testing | 3 | Critical |
| T8 | Deployment pipeline | 2 | Medium |
| T9 | Final release | 1 | Critical |

Dependencies:

- T4 depends on T2 and T5.
- T7 depends on T3, T4, and T6.
- T9 depends on T7 and T8.

### Stochastic Events (Seeded)

| Day | Event |
| --- | --- |
| Day 6 | `backend_lead` unavailable for 2 days |
| Day 10 | Payment integration requires +2 extra days |

### Tradeoffs Tested

- Start long-running work early vs finish short work first.
- Reallocate staff during temporary critical-skill loss.
- Decide when overtime is worth burnout cost.
- Decide which lower-priority work can be delayed safely.

Greedy shortest-task-first policies often miss the deadline because critical long work starts too late.

### Expected Performance

| Policy | Expected Score |
| --- | --- |
| Random | 0.10–0.20 |
| Heuristic Baseline | 0.55–0.70 |
| Strong Agent | 0.75–0.85 |

---

## Hard Task — `enterprise_migration_crisis`

### Objective

Rescue a failing enterprise migration project under severe uncertainty.

### Why This Task Exists

This task evaluates advanced capability:

- long-term planning,
- risk management,
- prioritization under overlapping disruptions,
- strategic sacrifice of local objectives to preserve global success.

Local heuristics should not solve this task reliably.

### Configuration

| Property | Value |
| --- | --- |
| Employees | 5 |
| Tasks | 15 (+ mutually exclusive branch) |
| Deadline | 22 days |
| Budget | 130000 units |
| Max Episode Length | 25 steps |
| Random Seed | 9001 |

### Team

| Employee | Skills |
| --- | --- |
| `senior_backend` | backend |
| `senior_frontend` | frontend |
| `qa_lead` | testing |
| `architect` | backend, design |
| `contractor` | backend |

The `contractor` is initially unavailable and must be hired via contingency action.

### Hard-Mode God-Tier Features

- **Mutually Exclusive Branching (Buy vs Build)**: Task 8 and Task 15 cancel each other out.
- **The Mythical Man-Month**: 2+ developers on a task causes coordination slowdowns.
- **Pair-Programming Immunity**: 2+ developers on a task grants zero bugs spawned from Tech Debt.
- hidden critical-path dependencies,
- overlapping disruptions and time-lagged Technical Debt bugs,
- high burnout risk with downstream productivity impact.

### Major Disruptions

| Day | Event |
| --- | --- |
| Day 5 | `senior_backend` unavailable for 3 days |
| Day 9 | Compliance review adds a new mandatory task |
| Day 12 | Vendor integration delayed by +3 days |
| Day 15 | If average burnout > 0.75, `qa_lead` productivity drops by 50% |

### Strategic Decisions Required

- Hire contractor now (budget hit) or defer (capacity risk)?
- Drop optional documentation to protect release date?
- Use overtime now despite delayed burnout penalties?
- Use architect immediately for unblock vs reserve for future disruptions?

Correct actions are highly state-dependent and time-dependent.

### Why This Task Is Hard

Decision effects are delayed and interacting.

Example:

- Day 7 overtime improves short-term throughput.
- Day 15 burnout penalty reduces testing productivity and harms final score.

Agents must plan several steps ahead rather than maximize immediate reward.

### Expected Performance

| Policy | Expected Score |
| --- | --- |
| Random | 0.00–0.05 |
| Heuristic Baseline | 0.13 |
| Strong Agent | 0.30–0.50 |

---

## Difficulty Progression Summary

| Property | Easy | Medium | Hard |
| --- | --- | --- | --- |
| Tasks | 5 | 9 | 14 |
| Employees | 3 | 4 | 5 |
| Long-running Tasks | No | Yes | Yes |
| Burnout | No | Yes | Yes |
| Stochastic Events | None | 2 | 4 |
| Budget Tradeoffs | Minimal | Moderate | Strong |
| Hidden Dependencies | No | Partial | Yes |
| Required Planning Horizon | Low | Medium | High |

---

## Alignment with Evaluation Criteria

### Real-World Utility

The tasks mirror realistic software delivery contexts:

- small web launch,
- startup MVP crunch,
- enterprise migration crisis.

### Task and Grader Quality

Each task has:

- a clear objective,
- deterministic scoring,
- a meaningful easy → medium → hard progression.

### RL Suitability

Across tasks, the environment includes:

- dependency constraints,
- long-running work,
- deterministic disruptions,
- tradeoffs across speed, cost, and team health.

These properties make the benchmark well-suited for reinforcement learning evaluation.

