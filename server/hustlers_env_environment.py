# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Adaptive Project Manager Environment Implementation.

Simulates software project management under uncertainty.
"""

import copy
import random
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import (
        ProjectAction, ProjectObservation, ProjectState,
        TaskState, EmployeeState, RiskState, Assignment,
        HustlersAction, HustlersObservation,
    )
    from ..tasks import TASK_REGISTRY
    from ..graders import GRADER_REGISTRY
except ImportError:
    from models import (
        ProjectAction, ProjectObservation, ProjectState,
        TaskState, EmployeeState, RiskState, Assignment,
        HustlersAction, HustlersObservation,
    )
    from tasks import TASK_REGISTRY
    from graders import GRADER_REGISTRY


class AdaptiveProjectManagerEnv(Environment):
    """
    Adaptive Project Manager Environment.

    Simulates software project management under uncertainty where agents must:
    - Assign employees to tasks based on skills
    - Handle dynamic events (employee illness, scope changes)
    - Balance workload to prevent burnout
    - Complete critical path tasks before deadline

    Example:
        >>> env = AdaptiveProjectManagerEnv()
        >>> obs = env.reset("easy")
        >>> action = ProjectAction(assignments=[Assignment(employee_id="emp_1", task_id="task_1")])
        >>> obs = env.step(action)
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    # --- Configurable Constants ---
    # Burnout mechanics
    BURNOUT_WORK_RATE = 0.15           # Burnout increase per day of work
    BURNOUT_RECOVERY_RATE = 0.05       # Burnout decrease per day of rest
    BURNOUT_OVERTIME_RATE = 0.10       # Additional burnout from overtime
    BURNOUT_PRODUCTIVITY_THRESHOLD = 0.8  # Burnout level that triggers productivity penalty
    BURNOUT_PRODUCTIVITY_PENALTY = 0.5    # Productivity multiplier when burned out
    BURNOUT_COLLAPSE_THRESHOLD = 0.9      # Burnout level considered "collapsed"

    # Productivity mechanics
    COORDINATION_OVERHEAD = 0.15       # Per-extra-employee coordination penalty
    OVERTIME_PRODUCTIVITY_BOOST = 1.2  # Productivity multiplier during overtime
    OVERTIME_PRODUCTIVITY_CAP = 1.5    # Max productivity modifier from overtime
    CONTRACTOR_PRODUCTIVITY = 0.8      # Contractor productivity vs full-time
    RAMP_UP_PENALTY = 0.5              # Productivity multiplier on first day of new task
    EFFORT_UNCERTAINTY_MIN = 0.8       # Min effort multiplier (task easier than estimated)
    EFFORT_UNCERTAINTY_MAX = 1.4       # Max effort multiplier (task harder than estimated)

    # Reward shaping
    REWARD_CRITICAL_TASK = 5.0
    REWARD_NORMAL_TASK = 2.0
    REWARD_UNBLOCK = 1.0
    REWARD_CRITICAL_PATH_BONUS = 1.5   # Per downstream task unblocked by completing a blocker
    REWARD_SKILL_MATCH = 0.5
    PENALTY_TIME_COST = 0.25
    PENALTY_OVERDUE_CRITICAL = 3.0
    PENALTY_BURNOUT_THRESHOLD = 0.6
    PENALTY_BURNOUT_MULTIPLIER = 2.0
    PENALTY_REASSIGNMENT = 0.5
    REWARD_NORMALIZE_FACTOR = 10.0

    # Technical debt mechanics (medium/hard only)
    TECH_DEBT_QUALITY_THRESHOLD = 0.5  # Below this, rushed work spawns bugs
    TECH_DEBT_OVERTIME_PENALTY = 0.7   # Quality multiplier when overtime is active
    TECH_DEBT_BUG_EFFORT_RATIO = 0.4   # Bug effort as fraction of original task effort
    TECH_DEBT_MIN_DELAY = 2            # Min days before bug appears
    TECH_DEBT_MAX_DELAY = 4            # Max days before bug appears

    def __init__(self):
        """Initialize the environment."""
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._project_state: Optional[ProjectState] = None
        self._task_config: Dict[str, Any] = {}
        self._rng: Optional[random.Random] = None
        self._previous_assignments: Dict[str, str] = {}  # employee_id -> task_id
        self._messages: List[str] = []
        self._cumulative_reward: float = 0.0
        self._done: bool = False
        self._pending_bugs: List[Dict[str, Any]] = []  # Scheduled bug tasks from tech debt

    def reset(self, seed: Optional[int] = None, episode_id: Optional[str] = None, task_id: str = "easy", **kwargs) -> ProjectObservation:
        """
        Reset the environment with a specific task.

        Args:
            seed: Random seed (ignored, we use task-specific seeds)
            episode_id: Episode identifier (ignored, we generate our own)
            task_id: Task identifier ("easy", "medium", "hard" or aliases)
            **kwargs: Additional arguments (ignored)

        Returns:
            Initial ProjectObservation
        """
        # Normalize task_id
        task_id_normalized = task_id.lower().strip()
        
        # Get task configuration
        if task_id_normalized not in TASK_REGISTRY:
            raise ValueError(f"Unknown task: {task_id}. Available: {list(TASK_REGISTRY.keys())}")
        
        self._task_config = TASK_REGISTRY[task_id_normalized]()
        
        # Initialize RNG with task seed for reproducibility
        self._rng = random.Random(self._task_config["seed"])
        
        # Reset state
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._previous_assignments = {}
        self._messages = []
        self._cumulative_reward = 0.0
        self._done = False
        self._pending_bugs = []
        
        # Create project state from task config
        self._project_state = ProjectState(
            day=1,
            total_days=self._task_config["total_days"],
            budget_total=self._task_config["budget_total"],
            budget_spent=0.0,
            tasks=[TaskState(**t.model_dump()) if isinstance(t, TaskState) else TaskState(**t) 
                   for t in self._task_config["tasks"]],
            employees=[EmployeeState(**e.model_dump()) if isinstance(e, EmployeeState) else EmployeeState(**e) 
                       for e in self._task_config["employees"]],
            risks=[RiskState(**r.model_dump()) if isinstance(r, RiskState) else RiskState(**r) 
                   for r in self._task_config["risks"]],
            completed_tasks=[],
            overtime_active=False,
            contractor_hired=False,
            low_priority_deferred=False,
            stakeholder_satisfaction=1.0,
            task_id=task_id_normalized,
        )
        
        # Initial message
        self._messages = [f"Project '{self._task_config['name']}' started. Day 1 of {self._project_state.total_days}."]
        
        return self._create_observation()

    def step(self, action: ProjectAction) -> ProjectObservation:
        """
        Execute one step (one project day).

        Args:
            action: ProjectAction with assignments and contingency actions

        Returns:
            ProjectObservation with updated state
        """
        if self._project_state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        
        if self._done:
            return self._create_observation()
        
        self._state.step_count += 1
        self._messages = []
        
        # Store previous assignments for reassignment penalty
        prev_assignments = {e.id: e.assigned_task_id for e in self._project_state.employees}
        
        # 0. Advance day first (events trigger on the new day)
        self._project_state.day += 1
        
        # 0.5 Process any pending bug tasks from technical debt
        self._process_pending_bugs()
        
        # 1. Process scheduled events for this day
        self._process_scheduled_events()
        
        # 2. Apply contingency actions
        self._apply_contingency(action.contingency_action)
        
        # 3. Process task reprioritization
        self._process_reprioritization(action.reprioritized_tasks)
        
        # 4. Process assignments
        self._process_assignments(action.assignments)
        
        # 5. Progress work on tasks
        newly_completed, newly_unblocked = self._progress_work()
        
        # 6. Update burnout and workload
        self._update_burnout()
        
        # 7. Update budget
        self._update_budget()
        
        # 8. Calculate reward
        reward = self._calculate_reward(
            newly_completed=newly_completed,
            newly_unblocked=newly_unblocked,
            action=action,
            prev_assignments=prev_assignments,
        )
        self._cumulative_reward += reward
        
        # 9. Update stakeholder satisfaction
        self._update_stakeholder_satisfaction()
        
        # 10. Check termination
        self._check_termination()
        
        return self._create_observation(reward=reward)

    @property
    def state(self) -> State:
        """Get the current environment state."""
        return self._state

    def get_project_state(self) -> ProjectState:
        """Get the full project state for grading."""
        if self._project_state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        return self._project_state

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _create_observation(self, reward: float = 0.0) -> ProjectObservation:
        """Create an observation from the current state."""
        ps = self._project_state
        
        # Calculate derived values
        total_effort = sum(t.original_effort for t in ps.tasks)
        completed_effort = sum(t.original_effort for t in ps.tasks if t.status == "done")
        project_completion = completed_effort / total_effort if total_effort > 0 else 0.0
        
        blocked_tasks = sum(1 for t in ps.tasks if t.status == "blocked")
        overdue_tasks = sum(1 for t in ps.tasks 
                          if t.deadline_day and t.deadline_day < ps.day and t.status != "done")
        
        avg_burnout = sum(e.burnout for e in ps.employees) / len(ps.employees) if ps.employees else 0.0
        
        # Critical path progress
        critical_tasks = [t for t in ps.tasks if t.is_critical_path]
        if critical_tasks:
            critical_done = sum(1 for t in critical_tasks if t.status == "done")
            critical_progress = critical_done / len(critical_tasks)
        else:
            critical_progress = 1.0
        
        message = " | ".join(self._messages) if self._messages else "Day progressed normally."
        
        # Compute final score if done
        info = {}
        computed_final_score = None
        if self._done:
            grader = GRADER_REGISTRY.get(ps.task_id, GRADER_REGISTRY["easy"])
            computed_final_score = grader(ps)
            info["final_score"] = computed_final_score
        
        return ProjectObservation(
            day=ps.day,
            days_remaining=ps.total_days - ps.day,
            budget_remaining=ps.budget_total - ps.budget_spent,
            project_completion=project_completion,
            blocked_tasks=blocked_tasks,
            overdue_tasks=overdue_tasks,
            average_burnout=avg_burnout,
            tasks=[TaskState(**t.model_dump()) for t in ps.tasks],
            employees=[EmployeeState(**e.model_dump()) for e in ps.employees],
            risks=[RiskState(**r.model_dump()) for r in ps.risks],
            message=message,
            critical_path_progress=critical_progress,
            done=self._done,
            reward=reward,
            metadata=info,
            final_score=computed_final_score,  # Direct field for serialization
        )

    def _process_scheduled_events(self):
        """Process any scheduled events for the current day."""
        ps = self._project_state
        events = self._task_config.get("scheduled_events", [])
        
        for event in events:
            if event["day"] != ps.day:
                continue
            
            event_type = event["type"]
            
            if event_type == "employee_unavailable":
                emp_id = event["employee_id"]
                duration = event["duration"]
                for emp in ps.employees:
                    if emp.id == emp_id:
                        emp.available = False
                        emp.unavailable_until = ps.day + duration
                        # Unassign from current task
                        if emp.assigned_task_id:
                            for task in ps.tasks:
                                if task.id == emp.assigned_task_id:
                                    task.assigned_employees = [e for e in task.assigned_employees if e != emp_id]
                            emp.assigned_task_id = None
                        self._messages.append(event["message"])
                        
            elif event_type == "task_effort_increase":
                task_id = event["task_id"]
                increase = event["effort_increase"]
                for task in ps.tasks:
                    if task.id == task_id and task.status != "done":
                        task.remaining_effort += increase
                        self._messages.append(event["message"])
                        
            elif event_type == "add_task":
                new_task_data = event["task"]
                new_task = TaskState(**new_task_data) if isinstance(new_task_data, dict) else new_task_data
                ps.tasks.append(new_task)
                self._messages.append(event["message"])
                
            elif event_type == "burnout_check":
                threshold = event["threshold"]
                avg_burnout = sum(e.burnout for e in ps.employees) / len(ps.employees) if ps.employees else 0
                if avg_burnout > threshold:
                    affected_skills = event["affected_skills"]
                    penalty = event["productivity_penalty"]
                    for emp in ps.employees:
                        if any(skill in emp.skills for skill in affected_skills):
                            emp.productivity_modifier *= penalty
                    self._messages.append(event["message"])
            
            # Mark associated risk as triggered
            for risk in ps.risks:
                if risk.trigger_day == ps.day and not risk.triggered:
                    risk.triggered = True

    def _apply_contingency(self, contingency: str):
        """Apply contingency action effects."""
        ps = self._project_state
        
        if contingency == "request_overtime":
            ps.overtime_active = True
            # Overtime increases productivity but also burnout
            for emp in ps.employees:
                if emp.available:
                    emp.productivity_modifier = min(
                        emp.productivity_modifier * self.OVERTIME_PRODUCTIVITY_BOOST,
                        self.OVERTIME_PRODUCTIVITY_CAP
                    )
            self._messages.append("Overtime requested - productivity +20%, burnout increases faster")
            
        elif contingency == "hire_contractor":
            if not ps.contractor_hired:
                ps.contractor_hired = True
                # Add a contractor employee with general skills
                contractor = EmployeeState(
                    id="contractor_1",
                    name="Contractor",
                    skills=["frontend", "backend", "testing"],  # Versatile but not specialized
                    available=True,
                    workload=0.0,
                    burnout=0.0,
                    productivity_modifier=self.CONTRACTOR_PRODUCTIVITY,
                )
                ps.employees.append(contractor)
                # Contractors cost more
                ps.budget_spent += self._task_config.get("daily_burn_rate", 3000) * 2
                self._messages.append("Contractor hired - adds flexibility but increases costs")
                
        elif contingency == "defer_low_priority_work":
            if not ps.low_priority_deferred:
                ps.low_priority_deferred = True
                for task in ps.tasks:
                    if task.priority == "low" and task.status in ["todo", "in_progress"]:
                        task.status = "blocked"
                        # Remove any assignments
                        for emp_id in task.assigned_employees:
                            for emp in ps.employees:
                                if emp.id == emp_id:
                                    emp.assigned_task_id = None
                        task.assigned_employees = []
                self._messages.append("Low priority work deferred to focus on critical tasks")
                
        elif contingency == "request_emergency_funding":
            # Massive budget influx, but permanently damages stakeholder satisfaction
            ps.budget_total += 20000.0
            ps.stakeholder_satisfaction = max(0.0, ps.stakeholder_satisfaction - 0.15)
            self._messages.append("Emergency funding requested - Budget +$20k, but Stakeholders are unhappy!")

    def _process_reprioritization(self, task_ids: List[str]):
        """Process task reprioritization."""
        ps = self._project_state
        for task_id in task_ids:
            for task in ps.tasks:
                if task.id == task_id and task.priority != "critical":
                    task.priority = "critical"
                    task.is_critical_path = True

    def _process_assignments(self, assignments: List[Assignment]):
        """Process employee-task assignments."""
        ps = self._project_state
        
        for assignment in assignments:
            emp_id = assignment.employee_id
            task_id = assignment.task_id
            
            # Find employee
            emp = next((e for e in ps.employees if e.id == emp_id), None)
            if emp is None:
                continue
            
            # Check if employee is available
            if not emp.available:
                continue
            
            # Find task
            task = next((t for t in ps.tasks if t.id == task_id), None)
            if task is None:
                continue
            
            # Check if task is available for assignment
            if task.status == "done":
                continue
            
            # Check dependencies - can't work on blocked tasks
            if self._has_unmet_dependencies(task):
                task.status = "blocked"
                continue
            
            # Remove from previous assignment if any
            if emp.assigned_task_id and emp.assigned_task_id != task_id:
                prev_task = next((t for t in ps.tasks if t.id == emp.assigned_task_id), None)
                if prev_task:
                    prev_task.assigned_employees = [e for e in prev_task.assigned_employees if e != emp_id]
            
            # Track ramp-up: reset counter if this is a new task for the employee
            if emp.assigned_task_id != task_id:
                emp.days_on_current_task = 0  # Just assigned — ramp-up penalty applies
            
            # Make assignment
            emp.assigned_task_id = task_id
            if emp_id not in task.assigned_employees:
                task.assigned_employees.append(emp_id)
            
            # Effort estimation uncertainty: when a task starts for the first time,
            # reveal that the actual effort differs from the estimate.
            # This models the real-world fact that effort estimates are never perfect.
            if task.status == "todo":
                effort_multiplier = self._rng.uniform(
                    self.EFFORT_UNCERTAINTY_MIN,
                    self.EFFORT_UNCERTAINTY_MAX
                )
                task.remaining_effort *= effort_multiplier
                if abs(effort_multiplier - 1.0) > 0.1:
                    direction = "harder" if effort_multiplier > 1.0 else "easier"
                    self._messages.append(
                        f"Task '{task.name}' turns out to be {direction} than estimated "
                        f"(effort: {task.original_effort:.1f} -> {task.remaining_effort:.1f})"
                    )
                
                # Apply fixed cost upfront if any
                if task.fixed_cost > 0:
                    ps.budget_spent += task.fixed_cost
                    self._messages.append(f"Paid fixed cost of ${task.fixed_cost:,.2f} to begin task '{task.name}'")
            
            task.status = "in_progress"
            emp.workload = 1.0  # Full workload when assigned

    def _has_unmet_dependencies(self, task: TaskState) -> bool:
        """Check if task has unmet dependencies."""
        ps = self._project_state
        for dep_id in task.dependencies:
            dep_task = next((t for t in ps.tasks if t.id == dep_id), None)
            if dep_task and dep_task.status != "done":
                return True
        return False

    def _count_downstream_blocked(self, completed_task_id: str) -> int:
        """
        Count how many tasks are transitively blocked by a given task.
        
        If completing task_1 unblocks task_3, which in turn would unblock task_5,
        then downstream count for task_1 = 2.
        
        This drives the critical path bonus: clearing a deep blocker is worth
        more than completing a leaf task.
        """
        ps = self._project_state
        count = 0
        queue = [completed_task_id]
        visited = {completed_task_id}
        
        while queue:
            current_id = queue.pop(0)
            for task in ps.tasks:
                if task.id in visited:
                    continue
                if current_id in task.dependencies and task.status != "done":
                    count += 1
                    visited.add(task.id)
                    queue.append(task.id)
        
        return count

    def _check_task_quality(self, task: TaskState):
        """
        Check if a completed task was rushed or done with poor skill match.
        If so, schedule a bug task to spawn later via technical debt.
        Immunity granted if Pair Programming (2+ developers) is utilized!
        """
        ps = self._project_state
        
        if not task.assigned_employees:
            return
            
        # Pair Programming Immunity (God-Tier Feature)
        # Assigning multiple people to a task nullifies tech debt completely
        # as a strategic defense mechanism to counter the coordination tax.
        if len(task.assigned_employees) >= 2:
            return
            
        # Calculate quality based on skill match
        skill_scores = []
        for emp_id in task.assigned_employees:
            emp = next((e for e in ps.employees if e.id == emp_id), None)
            if not emp:
                continue
            if task.required_skill in emp.skills:
                skill_scores.append(1.0)
            elif any(s in task.required_skill or task.required_skill in s for s in emp.skills):
                skill_scores.append(0.5)
            else:
                skill_scores.append(0.0)
                
        avg_skill = sum(skill_scores) / len(skill_scores) if skill_scores else 0.0
        
        # Penalize quality for overtime
        if ps.overtime_active:
            avg_skill *= self.TECH_DEBT_OVERTIME_PENALTY
            
        if avg_skill < self.TECH_DEBT_QUALITY_THRESHOLD:
            # Task was rushed or done poorly. Spawn a bug!
            bug_effort = max(1.0, task.original_effort * self.TECH_DEBT_BUG_EFFORT_RATIO)
            delay = self._rng.randint(self.TECH_DEBT_MIN_DELAY, self.TECH_DEBT_MAX_DELAY)
            
            # Use original ID to generate deterministic bug ID
            bug_id = f"bug_{task.id}_{ps.day}"
            
            self._pending_bugs.append({
                "trigger_day": ps.day + delay,
                "task": TaskState(
                    id=bug_id,
                    name=f"[BUG] Fix {task.name}",
                    description=f"Technical debt from rushing {task.name}",
                    required_skill=task.required_skill,
                    original_effort=bug_effort,
                    remaining_effort=bug_effort,
                    priority="high",
                    status="todo",
                    dependencies=[],
                    is_critical_path=False,
                )
            })

    def _process_pending_bugs(self):
        """Add any triggered bugs to the task list."""
        ps = self._project_state
        still_pending = []
        for bug_info in self._pending_bugs:
            if ps.day >= bug_info["trigger_day"]:
                bug_task = bug_info["task"]
                ps.tasks.append(bug_task)
                self._messages.append(f"🚨 Technical Debt: Bug discovered in '{bug_task.name}'! Added to backlog.")
            else:
                still_pending.append(bug_info)
        self._pending_bugs = still_pending

    def _progress_work(self) -> Tuple[List[str], List[str]]:
        """Progress work on all in-progress tasks. Returns (completed, unblocked) task IDs."""
        ps = self._project_state
        newly_completed = []
        newly_unblocked = []
        
        for task in ps.tasks:
            if task.status != "in_progress":
                continue
            
            if not task.assigned_employees:
                continue
            
            # Calculate productivity
            productivity = self._calculate_productivity(task)
            
            # Increment ramp-up counters for all assigned employees
            # (after productivity calc so day 0 = penalty, day 1+ = full speed)
            for emp_id in task.assigned_employees:
                for emp in ps.employees:
                    if emp.id == emp_id:
                        emp.days_on_current_task += 1
            
            # Apply work
            task.remaining_effort -= productivity
            
            # Check if completed
            if task.remaining_effort <= 0:
                task.remaining_effort = 0
                task.status = "done"
                ps.completed_tasks.append(task.id)
                newly_completed.append(task.id)
                
                # Check if completion quality triggers technical debt (medium/hard only)
                if ps.task_id in ("medium", "hard"):
                    self._check_task_quality(task)
                
                # Check for mutually exclusive tasks (Buy vs Build)
                if task.mutually_exclusive_with:
                    mx_task = next((t for t in ps.tasks if t.id == task.mutually_exclusive_with), None)
                    if mx_task and mx_task.status != "done" and mx_task.status != "cancelled":
                        mx_task.status = "cancelled"
                        mx_task.remaining_effort = 0
                        mx_task.assigned_employees = []
                        self._messages.append(f"Branching Decision: '{task.name}' completed. Autocanceling alternative '{mx_task.name}'.")
                        
                        # Strip the cancelled task from all downstream dependencies
                        for other in ps.tasks:
                            if mx_task.id in other.dependencies:
                                other.dependencies.remove(mx_task.id)
                
                # Free up assigned employees
                for emp_id in task.assigned_employees:
                    for emp in ps.employees:
                        if emp.id == emp_id:
                            emp.assigned_task_id = None
                            emp.workload = 0.0
                            emp.days_on_current_task = 0
                task.assigned_employees = []
                
                # Check for newly unblocked tasks
                for other_task in ps.tasks:
                    if other_task.status == "blocked" or (other_task.status == "todo" and other_task.dependencies):
                        if task.id in other_task.dependencies or (task.mutually_exclusive_with and task.mutually_exclusive_with in other_task.dependencies):
                            if not self._has_unmet_dependencies(other_task):
                                if other_task.status == "blocked":
                                    other_task.status = "todo"
                                    newly_unblocked.append(other_task.id)
        
        return newly_completed, newly_unblocked

    def _calculate_productivity(self, task: TaskState) -> float:
        """
        Calculate productivity for a task.
        
        productivity = sum(skill_match_scores) * coordination_factor
        coordination_factor = 1 / (1 + 0.15 * (n_assigned - 1))
        """
        ps = self._project_state
        
        skill_scores = []
        for emp_id in task.assigned_employees:
            emp = next((e for e in ps.employees if e.id == emp_id), None)
            if emp is None or not emp.available:
                continue
            
            # Calculate skill match
            if task.required_skill in emp.skills:
                skill_score = 1.0  # Exact match
            elif any(s in task.required_skill or task.required_skill in s for s in emp.skills):
                skill_score = 0.5  # Partial match
            else:
                skill_score = 0.0  # No match (still can contribute minimally)
            
            # Apply productivity modifier (burnout effects, etc.)
            skill_score *= emp.productivity_modifier
            
            # Apply burnout penalty
            if emp.burnout > self.BURNOUT_PRODUCTIVITY_THRESHOLD:
                skill_score *= self.BURNOUT_PRODUCTIVITY_PENALTY
            
            # Apply ramp-up penalty on first day of new task
            if emp.days_on_current_task == 0:
                skill_score *= self.RAMP_UP_PENALTY
            
            skill_scores.append(skill_score)
        
        if not skill_scores:
            return 0.0
        
        # Coordination factor
        n_assigned = len(skill_scores)
        coordination_factor = 1 / (1 + self.COORDINATION_OVERHEAD * (n_assigned - 1))
        
        return sum(skill_scores) * coordination_factor

    def _update_burnout(self):
        """Update burnout levels for all employees."""
        ps = self._project_state
        
        for emp in ps.employees:
            # Check if employee becomes available again
            if emp.unavailable_until and ps.day >= emp.unavailable_until:
                emp.available = True
                emp.unavailable_until = None
            
            if not emp.available:
                continue
            
            # Calculate recovery (1 if not working, 0 if working)
            recovery = 1.0 if emp.assigned_task_id is None else 0.0
            
            # Update burnout
            delta = self.BURNOUT_WORK_RATE * emp.workload - self.BURNOUT_RECOVERY_RATE * recovery
            
            # Additional burnout from overtime
            if ps.overtime_active and emp.assigned_task_id:
                delta += self.BURNOUT_OVERTIME_RATE
            
            emp.burnout = max(0.0, min(1.0, emp.burnout + delta))
            
            # Reset productivity modifier if overtime ends
            if not ps.overtime_active and emp.productivity_modifier > 1.0:
                emp.productivity_modifier = 1.0

    def _update_budget(self):
        """Update budget based on daily burn rate and active employees."""
        ps = self._project_state
        daily_rate = self._task_config.get("daily_burn_rate", 3000.0)
        
        # Active employees cost money
        active_count = sum(1 for e in ps.employees if e.available and e.id != "contractor_1")
        contractor_active = any(e.id == "contractor_1" and e.available for e in ps.employees)
        
        # Base cost
        ps.budget_spent += daily_rate
        
        # Extra cost for contractor
        if contractor_active:
            ps.budget_spent += daily_rate * 0.5  # 50% premium
        
        # Extra cost for overtime
        if ps.overtime_active:
            ps.budget_spent += daily_rate * 0.3  # 30% overtime premium

    def _calculate_reward(
        self,
        newly_completed: List[str],
        newly_unblocked: List[str],
        action: ProjectAction,
        prev_assignments: Dict[str, Optional[str]],
    ) -> float:
        """
        Calculate step reward.
        
        reward = (
            5 * newly_completed_critical_tasks
            + 2 * newly_completed_normal_tasks
            + 1 * newly_unblocked_tasks
            + 0.5 * skill_match_count
            - 0.25
            - 3 * overdue_critical_tasks
            - burnout_penalty
            - reassignment_penalty
        )
        """
        ps = self._project_state
        reward = 0.0
        
        # Reward for completed tasks
        for task_id in newly_completed:
            task = next((t for t in ps.tasks if t.id == task_id), None)
            if task:
                if task.is_critical_path or task.priority == "critical":
                    reward += self.REWARD_CRITICAL_TASK
                else:
                    reward += self.REWARD_NORMAL_TASK
        
        # Reward for unblocked tasks (flat per unblock)
        reward += self.REWARD_UNBLOCK * len(newly_unblocked)
        
        # Critical path bonus: reward completing tasks that unblock downstream work
        for task_id in newly_completed:
            downstream = self._count_downstream_blocked(task_id)
            if downstream > 0:
                reward += self.REWARD_CRITICAL_PATH_BONUS * downstream
        
        # Reward for good skill matches in assignments
        skill_match_count = 0
        for assignment in action.assignments:
            emp = next((e for e in ps.employees if e.id == assignment.employee_id), None)
            task = next((t for t in ps.tasks if t.id == assignment.task_id), None)
            if emp and task and task.required_skill in emp.skills:
                skill_match_count += 1
        reward += self.REWARD_SKILL_MATCH * skill_match_count
        
        # Base cost per step
        reward -= self.PENALTY_TIME_COST
        
        # Penalty for overdue critical tasks
        overdue_critical = sum(1 for t in ps.tasks 
                               if t.is_critical_path and t.status != "done" 
                               and ps.day > ps.total_days * 0.8)  # Late in project
        reward -= self.PENALTY_OVERDUE_CRITICAL * overdue_critical
        
        # Burnout penalty
        avg_burnout = sum(e.burnout for e in ps.employees) / len(ps.employees) if ps.employees else 0
        if avg_burnout > self.PENALTY_BURNOUT_THRESHOLD:
            reward -= (avg_burnout - self.PENALTY_BURNOUT_THRESHOLD) * self.PENALTY_BURNOUT_MULTIPLIER
        
        # Reassignment penalty
        reassignment_count = 0
        for assignment in action.assignments:
            prev_task = prev_assignments.get(assignment.employee_id)
            if prev_task and prev_task != assignment.task_id:
                # Check if previous task is still in progress
                prev_task_obj = next((t for t in ps.tasks if t.id == prev_task), None)
                if prev_task_obj and prev_task_obj.status == "in_progress":
                    reassignment_count += 1
        reward -= self.PENALTY_REASSIGNMENT * reassignment_count
        
        # Normalize to reasonable range, then scale to [-1, 1] for compatibility
        normalized_reward = max(-1.0, min(1.0, reward / self.REWARD_NORMALIZE_FACTOR))
        
        return normalized_reward

    def _update_stakeholder_satisfaction(self):
        """Update stakeholder satisfaction based on project progress."""
        ps = self._project_state
        
        # Calculate expected progress
        expected_progress = ps.day / ps.total_days
        
        # Calculate actual critical path progress
        critical_tasks = [t for t in ps.tasks if t.is_critical_path]
        if critical_tasks:
            actual_progress = sum(1 for t in critical_tasks if t.status == "done") / len(critical_tasks)
        else:
            actual_progress = expected_progress
        
        # Adjust satisfaction based on progress differential
        if actual_progress >= expected_progress:
            ps.stakeholder_satisfaction = min(1.0, ps.stakeholder_satisfaction + 0.02)
        else:
            gap = expected_progress - actual_progress
            ps.stakeholder_satisfaction = max(0.0, ps.stakeholder_satisfaction - gap * 0.1)

    def _check_termination(self):
        """Check if episode should terminate."""
        ps = self._project_state
        
        # Check if all tasks are done
        all_done = all(t.status == "done" for t in ps.tasks)
        if all_done:
            self._done = True
            self._messages.append("All tasks completed!")
            return
        
        # Check if deadline reached
        if ps.day >= ps.total_days:
            self._done = True
            self._messages.append(f"Deadline reached on day {ps.day}.")
            return
        
        # Check if budget exhausted
        if ps.budget_spent >= ps.budget_total:
            self._done = True
            self._messages.append("Budget exhausted.")
            return
        
        # Check if all available employees are burned out beyond recovery
        available_emps = [e for e in ps.employees if e.available]
        if available_emps and all(e.burnout >= self.BURNOUT_COLLAPSE_THRESHOLD for e in available_emps):
            self._done = True
            self._messages.append(
                "Team burnout collapse: all available employees are critically burned out. "
                "Project cannot continue."
            )
            return
        
        # Check for deadlock: remaining tasks exist but none can be worked on
        remaining_tasks = [t for t in ps.tasks if t.status not in ("done", "blocked")]
        blocked_or_done = [t for t in ps.tasks if t.status in ("done", "blocked")]
        workable_tasks = [
            t for t in ps.tasks
            if t.status in ("todo", "in_progress")
            and not self._has_unmet_dependencies(t)
        ]
        available_workers = [e for e in ps.employees if e.available]
        
        if not remaining_tasks and not all_done:
            # All non-done tasks are blocked — deadlock
            self._done = True
            self._messages.append(
                "Project deadlock: all remaining tasks are blocked with no path to resolution."
            )
            return
        
        if not workable_tasks and not available_workers and not all_done:
            # No one can work and nothing can be worked on
            self._done = True
            self._messages.append(
                "Project stalled: no available employees and no workable tasks."
            )
            return


# Legacy alias for backward compatibility
HustlersEnvironment = AdaptiveProjectManagerEnv
