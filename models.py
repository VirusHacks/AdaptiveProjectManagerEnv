# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Adaptive Project Manager Environment.

The AdaptiveProjectManagerEnv simulates software project management under uncertainty.
"""

from typing import Literal, Optional, List
from openenv.core.env_server.types import Action, Observation
from pydantic import BaseModel, Field


# ============================================================================
# State Models
# ============================================================================

class TaskState(BaseModel):
    """State of a single task in the project."""
    id: str = Field(..., description="Unique task identifier")
    name: str = Field(default="", description="Human-readable task name")
    priority: Literal["low", "medium", "high", "critical"] = Field(
        default="medium", description="Task priority level"
    )
    status: Literal["todo", "in_progress", "blocked", "done"] = Field(
        default="todo", description="Current task status"
    )
    required_skill: str = Field(..., description="Skill required to complete this task")
    remaining_effort: float = Field(default=1.0, description="Remaining effort in person-days")
    original_effort: float = Field(default=1.0, description="Original effort estimate")
    dependencies: List[str] = Field(default_factory=list, description="IDs of tasks this depends on")
    is_critical_path: bool = Field(default=False, description="Whether task is on critical path")
    assigned_employees: List[str] = Field(default_factory=list, description="IDs of assigned employees")
    deadline_day: Optional[int] = Field(default=None, description="Deadline day (if any)")


class EmployeeState(BaseModel):
    """State of a single employee."""
    id: str = Field(..., description="Unique employee identifier")
    name: str = Field(default="", description="Human-readable employee name")
    skills: List[str] = Field(default_factory=list, description="List of skills this employee has")
    available: bool = Field(default=True, description="Whether employee is available")
    assigned_task_id: Optional[str] = Field(default=None, description="Currently assigned task ID")
    workload: float = Field(default=0.0, description="Current workload (0-1)")
    burnout: float = Field(default=0.0, description="Current burnout level (0-1)")
    productivity_modifier: float = Field(default=1.0, description="Productivity modifier")
    unavailable_until: Optional[int] = Field(default=None, description="Day when employee becomes available again")


class RiskState(BaseModel):
    """State of a risk event."""
    id: str = Field(..., description="Unique risk identifier")
    name: str = Field(default="", description="Risk description")
    probability: float = Field(default=0.0, description="Probability of occurrence (0-1)")
    impact: str = Field(default="", description="Description of impact")
    triggered: bool = Field(default=False, description="Whether risk has been triggered")
    trigger_day: Optional[int] = Field(default=None, description="Day when risk triggers")
    mitigated: bool = Field(default=False, description="Whether risk has been mitigated")


class ProjectState(BaseModel):
    """Complete project state."""
    day: int = Field(default=1, description="Current project day")
    total_days: int = Field(default=30, description="Total project days allowed")
    budget_total: float = Field(default=100000.0, description="Total project budget")
    budget_spent: float = Field(default=0.0, description="Budget spent so far")
    tasks: List[TaskState] = Field(default_factory=list, description="All project tasks")
    employees: List[EmployeeState] = Field(default_factory=list, description="All employees")
    risks: List[RiskState] = Field(default_factory=list, description="All risks")
    completed_tasks: List[str] = Field(default_factory=list, description="IDs of completed tasks")
    overtime_active: bool = Field(default=False, description="Whether overtime is currently active")
    contractor_hired: bool = Field(default=False, description="Whether a contractor has been hired")
    low_priority_deferred: bool = Field(default=False, description="Whether low priority work is deferred")
    stakeholder_satisfaction: float = Field(default=1.0, description="Stakeholder satisfaction (0-1)")
    task_id: str = Field(default="", description="Current task/scenario ID")


# ============================================================================
# Action Models
# ============================================================================

class Assignment(BaseModel):
    """A single employee-to-task assignment."""
    employee_id: str = Field(..., description="ID of the employee to assign")
    task_id: str = Field(..., description="ID of the task to assign to")


class ProjectAction(Action):
    """Action for the Adaptive Project Manager environment."""
    assignments: List[Assignment] = Field(
        default_factory=list, 
        description="List of employee-task assignments"
    )
    reprioritized_tasks: List[str] = Field(
        default_factory=list, 
        description="List of task IDs to reprioritize to critical"
    )
    contingency_action: Literal[
        "none",
        "request_overtime",
        "hire_contractor",
        "defer_low_priority_work"
    ] = Field(default="none", description="Contingency action to take")


# ============================================================================
# Observation Model
# ============================================================================

class ProjectObservation(Observation):
    """Observation from the Adaptive Project Manager environment."""
    day: int = Field(default=1, description="Current project day")
    days_remaining: int = Field(default=30, description="Days remaining until deadline")
    budget_remaining: float = Field(default=100000.0, description="Remaining budget")
    project_completion: float = Field(default=0.0, description="Project completion percentage (0-1)")
    blocked_tasks: int = Field(default=0, description="Number of blocked tasks")
    overdue_tasks: int = Field(default=0, description="Number of overdue tasks")
    average_burnout: float = Field(default=0.0, description="Average team burnout (0-1)")
    tasks: List[TaskState] = Field(default_factory=list, description="All task states")
    employees: List[EmployeeState] = Field(default_factory=list, description="All employee states")
    risks: List[RiskState] = Field(default_factory=list, description="All risk states")
    message: str = Field(default="", description="Status message about recent events")
    critical_path_progress: float = Field(default=0.0, description="Critical path completion (0-1)")
    

# ============================================================================
# Legacy compatibility (keep old classes for any existing code)
# ============================================================================

class HustlersAction(Action):
    """Action for the Hustlers Env environment - just a message to echo."""
    message: str = Field(..., description="Message to echo back")


class HustlersObservation(Observation):
    """Observation from the Hustlers Env environment - the echoed message."""
    echoed_message: str = Field(default="", description="The echoed message")
    message_length: int = Field(default=0, description="Length of the echoed message")
