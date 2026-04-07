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
        if self._done:
            grader = GRADER_REGISTRY.get(ps.task_id, GRADER_REGISTRY["easy"])
            final_score = grader(ps)
            info["final_score"] = final_score
        
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
                    emp.productivity_modifier = min(emp.productivity_modifier * 1.2, 1.5)
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
                    productivity_modifier=0.8,  # Less productive than full-time
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
            
            # Make assignment
            emp.assigned_task_id = task_id
            if emp_id not in task.assigned_employees:
                task.assigned_employees.append(emp_id)
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
            
            # Apply work
            task.remaining_effort -= productivity
            
            # Check if completed
            if task.remaining_effort <= 0:
                task.remaining_effort = 0
                task.status = "done"
                ps.completed_tasks.append(task.id)
                newly_completed.append(task.id)
                
                # Free up assigned employees
                for emp_id in task.assigned_employees:
                    for emp in ps.employees:
                        if emp.id == emp_id:
                            emp.assigned_task_id = None
                            emp.workload = 0.0
                task.assigned_employees = []
                
                # Check for newly unblocked tasks
                for other_task in ps.tasks:
                    if other_task.status == "blocked" or (other_task.status == "todo" and other_task.dependencies):
                        if task.id in other_task.dependencies:
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
            if emp.burnout > 0.8:
                skill_score *= 0.5
            
            skill_scores.append(skill_score)
        
        if not skill_scores:
            return 0.0
        
        # Coordination factor
        n_assigned = len(skill_scores)
        coordination_factor = 1 / (1 + 0.15 * (n_assigned - 1))
        
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
            
            # Update burnout: burnout = burnout + 0.15 * workload - 0.05 * recovery
            delta = 0.15 * emp.workload - 0.05 * recovery
            
            # Additional burnout from overtime
            if ps.overtime_active and emp.assigned_task_id:
                delta += 0.1
            
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
                    reward += 5.0
                else:
                    reward += 2.0
        
        # Reward for unblocked tasks
        reward += 1.0 * len(newly_unblocked)
        
        # Reward for good skill matches in assignments
        skill_match_count = 0
        for assignment in action.assignments:
            emp = next((e for e in ps.employees if e.id == assignment.employee_id), None)
            task = next((t for t in ps.tasks if t.id == assignment.task_id), None)
            if emp and task and task.required_skill in emp.skills:
                skill_match_count += 1
        reward += 0.5 * skill_match_count
        
        # Base cost per step
        reward -= 0.25
        
        # Penalty for overdue critical tasks
        overdue_critical = sum(1 for t in ps.tasks 
                               if t.is_critical_path and t.status != "done" 
                               and ps.day > ps.total_days * 0.8)  # Late in project
        reward -= 3.0 * overdue_critical
        
        # Burnout penalty
        avg_burnout = sum(e.burnout for e in ps.employees) / len(ps.employees) if ps.employees else 0
        if avg_burnout > 0.6:
            reward -= (avg_burnout - 0.6) * 2.0
        
        # Reassignment penalty
        reassignment_count = 0
        for assignment in action.assignments:
            prev_task = prev_assignments.get(assignment.employee_id)
            if prev_task and prev_task != assignment.task_id:
                # Check if previous task is still in progress
                prev_task_obj = next((t for t in ps.tasks if t.id == prev_task), None)
                if prev_task_obj and prev_task_obj.status == "in_progress":
                    reassignment_count += 1
        reward -= 0.5 * reassignment_count
        
        # Normalize to reasonable range (roughly -2 to +10 per step)
        # Then scale to [-1, 1] range for compatibility
        normalized_reward = max(-1.0, min(1.0, reward / 10.0))
        
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


# Legacy alias for backward compatibility
HustlersEnvironment = AdaptiveProjectManagerEnv
