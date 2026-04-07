# AdaptiveProjectManagerEnv - Test Results & Analysis

**Date:** April 7, 2026  
**Environment:** Windows 11, Python 3.11, UV package manager  
**OpenEnv Version:** 0.2.2+

---

## Executive Summary

The AdaptiveProjectManagerEnv has been fully implemented and tested. All core functionality works correctly, including task management, employee assignments, burnout mechanics, scheduled events, and grading. The environment successfully differentiates between difficulty levels, with the easy task consistently scoring higher than medium and hard tasks using the same heuristic policy.

---

## 1. Unit Tests - Model Validation

### 1.1 Pydantic Models

| Model | Fields Tested | Status |
|-------|---------------|--------|
| `TaskState` | id, priority, status, required_skill, remaining_effort, dependencies, is_critical_path | ✅ Pass |
| `EmployeeState` | id, skills, available, assigned_task_id, workload, burnout | ✅ Pass |
| `ProjectAction` | assignments, reprioritized_tasks, contingency_action | ✅ Pass |
| `ProjectObservation` | day, days_remaining, budget_remaining, project_completion, tasks, employees | ✅ Pass |

**Observation:** All Pydantic models correctly validate input data and provide proper type hints. The models serialize/deserialize correctly for WebSocket communication.

---

## 2. Task Configuration Tests

### 2.1 Task Registry

| Task ID | Seed | Days | Employees | Tasks | Scheduled Events |
|---------|------|------|-----------|-------|------------------|
| `easy` | 42 | 12 | 3 | 5 | 0 |
| `medium` | 1337 | 18 | 4 | 9 | 2 |
| `hard` | 9001 | 25 | 5 | 14 | 4 |

**Analysis:**
- Easy task has no stochastic elements, making it purely a scheduling optimization problem
- Medium task introduces employee unavailability (day 6) and scope creep (day 10)
- Hard task has the most complex event chain: illness, compliance requirements, vendor delays, and burnout-triggered productivity loss

---

## 3. Environment Reset Tests

### 3.1 Initial State Verification

```
Test Results:
  easy:   Day 1, 5 tasks, 3 employees, 11 days remaining ✅
  medium: Day 1, 9 tasks, 4 employees, 17 days remaining ✅
  hard:   Day 1, 14 tasks, 5 employees, 24 days remaining ✅
```

**Observations:**
- `days_remaining` correctly calculates as `total_days - current_day`
- All tasks initialize with `status="todo"`
- All employees start with `burnout=0.0` and `available=True`
- Project completion starts at 0.0%

### 3.2 Reproducibility Test

```python
# Two separate environment instances with same task
env1.reset("easy") == env2.reset("easy")  # ✅ Identical states
```

**Analysis:** Fixed seeds ensure deterministic task generation. The same task ID always produces identical initial conditions, enabling fair benchmark comparisons.

---

## 4. Step Function Tests

### 4.1 Basic Step Execution

| Test Case | Input | Expected | Actual | Status |
|-----------|-------|----------|--------|--------|
| Empty action | `ProjectAction(assignments=[])` | Day advances | Day 1→2 | ✅ Pass |
| Single assignment | `Assignment(emp_1, task_1)` | Task in_progress | status=in_progress | ✅ Pass |
| Invalid employee | `Assignment(emp_99, task_1)` | Ignored | No error, no effect | ✅ Pass |

### 4.2 Task Completion Test

```
Test: Assign Alice (ui_design skill) to "Design Homepage" (2.0 effort)

Step 1: remaining_effort = 2.0 → ~1.0 (productivity ~1.0)
Step 2: remaining_effort = ~1.0 → ~0.0
Step 3: Task marked as "done"

Result: Task completed in 3 steps ✅
```

**Analysis:** Productivity calculation works correctly:
- Exact skill match yields 1.0 productivity
- Coordination factor of 1.0 (single employee)
- Total daily progress ≈ 1.0 effort units

### 4.3 Dependency Handling

```
Task graph (easy):
  task_1 (Design Homepage) ──┐
                              ├──► task_3 (Frontend) ──┐
  task_2 (Backend API) ──────┤                         ├──► task_5 (Testing)
                              └──► task_4 (Database) ──┘

Test: Attempt to assign task_3 before task_1 completes
Result: Task remains blocked until dependency satisfied ✅
```

---

## 5. Burnout System Tests

### 5.1 Burnout Accumulation

```
Initial burnout: 0.0
After 3 steps of continuous work:
  Step 1: 0.0 + 0.15×1.0 = 0.15
  Step 2: 0.15 + 0.15×1.0 = 0.30
  Step 3: 0.30 + 0.15×1.0 = 0.45

Actual measured: 0.45 ✅
```

### 5.2 Recovery Mechanics

```
Unassigned employee recovery:
  burnout -= 0.05 per step

Test: Employee at 0.45 burnout, unassigned for 2 steps
Expected: 0.45 - 0.10 = 0.35
Actual: 0.35 ✅
```

### 5.3 Burnout Productivity Penalty

```
Condition: Employee burnout > 0.8
Expected: 50% productivity reduction
Status: Implemented in _calculate_productivity() ✅
```

---

## 6. Contingency Action Tests

### 6.1 Request Overtime

| Metric | Before | After |
|--------|--------|-------|
| Productivity modifier | 1.0 | 1.2 |
| Burnout increase rate | +0.15/step | +0.25/step |
| Message | - | "Overtime requested..." |

**Status:** ✅ Pass

### 6.2 Hire Contractor

| Metric | Before | After |
|--------|--------|-------|
| Employee count | 3 | 4 |
| Contractor skills | - | [frontend, backend, testing] |
| Contractor productivity | - | 0.8 (80% of regular) |
| Budget impact | - | +2× daily burn rate |

**Status:** ✅ Pass

### 6.3 Defer Low Priority Work

```
Test with medium task (has 1 low-priority task):

Before: task_9 (Documentation) status = "todo"
After:  task_9 (Documentation) status = "blocked"

Status: ✅ Pass
```

---

## 7. Scheduled Events Tests

### 7.1 Medium Task Events

| Day | Event | Expected Behavior | Actual | Status |
|-----|-------|-------------------|--------|--------|
| 6 | Employee illness | Bob (emp_2) unavailable for 2 days | Bob.available=False, unavailable_until=8 | ✅ Pass |
| 10 | Scope creep | Payment task +2 effort | remaining_effort increased by 2.0 | ✅ Pass |

**Test Output:**
```
Testing medium task scheduled events...
After reset: Day 1
After step 5: Day 6, Bob available = False
  Message: Bob is sick and unavailable for 2 days
```

### 7.2 Hard Task Events

| Day | Event | Expected Behavior | Actual | Status |
|-----|-------|-------------------|--------|--------|
| 5 | Emergency leave | Bob unavailable 3 days | ✅ Verified |
| 9 | Compliance requirement | New task added (task_15) | Task count: 14→15 | ✅ Pass |
| 12 | Vendor delay | Vendor integration +3 effort | ✅ Verified |
| 15 | Burnout check | If avg_burnout > 0.6, QA productivity halves | ✅ Verified |

**Test Output:**
```
Testing hard task scheduled events...
After reset: Day 1, Tasks: 14
After step 8: Day 9, Tasks: 15
  Message: New compliance requirement: Compliance Audit task added
Compliance task found: True
```

---

## 8. Grading System Tests

### 8.1 Score Component Breakdown

The final score formula:
```
score = 0.35×completion + 0.25×deadline + 0.15×budget + 0.15×team_health + 0.10×stakeholder
```

### 8.2 Edge Case Testing

| Scenario | Expected Score | Actual Score | Status |
|----------|----------------|--------------|--------|
| Empty state (no tasks) | ~0.4 (base) | 0.400 | ✅ Pass |
| Perfect completion, early finish, low burnout | > 0.9 | 0.952-0.965 | ✅ Pass |
| Failed project (no tasks done, high burnout) | < 0.5 | 0.15-0.30 | ✅ Pass |

### 8.3 Score Bounds Verification

```
All graders tested for bound compliance:
  grade_easy(state) ∈ [0.0, 1.0] ✅
  grade_medium(state) ∈ [0.0, 1.0] ✅
  grade_hard(state) ∈ [0.0, 1.0] ✅
```

---

## 9. Full Episode Tests

### 9.1 Heuristic Policy Performance

**Policy:** Assign available employees to highest-priority tasks matching their skills.

| Task | Steps | Tasks Completed | Final Score | Total Reward |
|------|-------|-----------------|-------------|--------------|
| easy | 7 | 5/5 (100%) | 0.952 | 2.325 |
| medium | 17 | 7/9 (78%) | 0.665 | 2.075 |
| hard | 24 | 14/15 (93%) | 0.661 | 2.800 |

### 9.2 Difficulty Ordering Analysis

```
Expected: easy > medium > hard (same policy, different difficulty)
Actual:   0.952 > 0.665 > 0.661 ✅

Observation: The hard task actually completed more tasks (93% vs 78%) but
scored slightly lower than medium. This is due to:
1. Higher average burnout from longer project duration
2. Additional compliance task added dynamically
3. More complex dependency chains causing delays
```

### 9.3 Step Efficiency Analysis

| Task | Days Available | Steps Used | Efficiency |
|------|----------------|------------|------------|
| easy | 12 | 7 | 58% (5 days slack) |
| medium | 18 | 17 | 94% (1 day slack) |
| hard | 25 | 24 | 96% (1 day slack) |

**Observation:** The heuristic policy is more efficient on easy tasks, indicating that medium and hard tasks require more sophisticated planning to complete with slack time.

---

## 10. Reward System Analysis

### 10.1 Reward Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Critical task completion | +5.0 | Completing critical path tasks |
| Normal task completion | +2.0 | Completing non-critical tasks |
| Task unblocking | +1.0 | Freeing dependent tasks |
| Skill matching | +0.5 | Good employee-task assignments |
| Base cost | -0.25 | Per-step penalty |
| Overdue penalty | -3.0 | Critical tasks past 80% timeline |
| Burnout penalty | Variable | Based on avg burnout > 0.6 |
| Reassignment penalty | -0.5 | Changing employee assignments |

### 10.2 Reward Distribution

```
Easy task (7 steps):
  Total reward: 2.325
  Average per step: 0.332

Medium task (17 steps):
  Total reward: 2.075
  Average per step: 0.122

Hard task (24 steps):
  Total reward: 2.800
  Average per step: 0.117
```

**Analysis:** Easy tasks provide higher per-step rewards due to:
- Faster task completion (fewer steps per task)
- No event-driven penalties
- Lower burnout accumulation

---

## 11. OpenEnv Compatibility Tests

### 11.1 YAML Configuration

```yaml
spec_version: 1
name: adaptive-project-manager
type: space
runtime: fastapi
app: server.app:app
port: 8000
tasks:
  - easy
  - medium
  - hard
```

**Status:** ✅ Valid OpenEnv configuration

### 11.2 API Compliance

| Method | Signature | Status |
|--------|-----------|--------|
| `reset` | `reset(task_id: str) -> Observation` | ✅ Compliant |
| `step` | `step(action: Action) -> Observation` | ✅ Compliant |
| `state` | `state() -> State` | ✅ Compliant |

### 11.3 Inference Script Output Format

```
[START] task=easy
[STEP] day=2 action={"assignments":[{"e":"emp_1","t":"task_1"}],"contingency":"none"} reward=0.50
[STEP] day=3 action={"assignments":[{"e":"emp_2","t":"task_2"}],"contingency":"none"} reward=0.75
...
[END] task=easy score=0.85
```

**Status:** ✅ Compliant with OpenEnv stdout format requirements

---

## 12. Performance Observations

### 12.1 Execution Time

| Operation | Time |
|-----------|------|
| Environment reset | < 1ms |
| Single step | < 1ms |
| Full easy episode (7 steps) | ~5ms |
| Full hard episode (25 steps) | ~15ms |

**Conclusion:** Environment is highly efficient, suitable for large-scale RL training.

### 12.2 Memory Usage

- Base environment: ~50KB
- Per-task state: ~5-10KB
- No memory leaks observed during multi-episode tests

---

## 13. Known Limitations & Future Improvements

### 13.1 Current Limitations

1. **Single-threaded execution:** No parallel task processing simulation
2. **Fixed skill matching:** Binary exact/partial/no match (could be more nuanced)
3. **No communication modeling:** Team collaboration not simulated
4. **Deterministic events only:** No true stochastic risk triggers

### 13.2 Potential Enhancements

1. Add inter-employee collaboration bonuses
2. Implement skill development over time
3. Add stakeholder meeting events that pause work
4. Include technical debt mechanics
5. Model employee morale beyond burnout

---

## 14. Conclusion

The AdaptiveProjectManagerEnv successfully implements all required OpenEnv specifications:

| Requirement | Status |
|-------------|--------|
| Typed Pydantic models | ✅ |
| reset(), step(), state() methods | ✅ |
| Deterministic task graders | ✅ |
| 3 difficulty levels (easy, medium, hard) | ✅ |
| Scores in [0.0, 1.0] | ✅ |
| Reproducible seeds | ✅ |
| Working Dockerfile | ✅ |
| Working inference.py | ✅ |
| OpenEnv-compatible YAML | ✅ |
| Structured stdout logs | ✅ |

The environment provides a rich simulation of software project management with meaningful decision-making challenges across difficulty levels. The heuristic baseline demonstrates that simple policies can solve easy tasks but struggle with the complexity introduced in medium and hard scenarios, leaving room for RL agents to discover more sophisticated strategies.

---

*Report generated: April 7, 2026*
