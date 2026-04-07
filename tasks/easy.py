# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Easy Task: Small Web Launch

Seed: 42
- 3 employees
- 5 tasks
- 12 day limit
- No stochastic events
"""

from typing import Dict, Any, List
from models import TaskState, EmployeeState, RiskState


def get_easy_task() -> Dict[str, Any]:
    """
    Generate the easy task configuration: Small Web Launch.
    
    A straightforward web project with clear dependencies and no surprises.
    """
    return {
        "task_id": "easy",
        "name": "Small Web Launch",
        "seed": 42,
        "total_days": 12,
        "budget_total": 50000.0,
        "daily_burn_rate": 2000.0,  # Cost per day
        "employees": get_employees(),
        "tasks": get_tasks(),
        "risks": get_risks(),
        "scheduled_events": [],  # No stochastic events for easy
    }


def get_employees() -> List[EmployeeState]:
    """Create 3 employees for the easy task."""
    return [
        EmployeeState(
            id="emp_1",
            name="Alice",
            skills=["frontend", "ui_design"],
            available=True,
            workload=0.0,
            burnout=0.0,
            productivity_modifier=1.0,
        ),
        EmployeeState(
            id="emp_2",
            name="Bob",
            skills=["backend", "database"],
            available=True,
            workload=0.0,
            burnout=0.0,
            productivity_modifier=1.0,
        ),
        EmployeeState(
            id="emp_3",
            name="Carol",
            skills=["testing", "frontend"],
            available=True,
            workload=0.0,
            burnout=0.0,
            productivity_modifier=1.0,
        ),
    ]


def get_tasks() -> List[TaskState]:
    """Create 5 tasks for the easy task."""
    return [
        TaskState(
            id="task_1",
            name="Design Homepage",
            priority="high",
            status="todo",
            required_skill="ui_design",
            remaining_effort=2.0,
            original_effort=2.0,
            dependencies=[],
            is_critical_path=True,
        ),
        TaskState(
            id="task_2",
            name="Setup Backend API",
            priority="high",
            status="todo",
            required_skill="backend",
            remaining_effort=3.0,
            original_effort=3.0,
            dependencies=[],
            is_critical_path=True,
        ),
        TaskState(
            id="task_3",
            name="Build Frontend Components",
            priority="medium",
            status="todo",
            required_skill="frontend",
            remaining_effort=3.0,
            original_effort=3.0,
            dependencies=["task_1"],
            is_critical_path=True,
        ),
        TaskState(
            id="task_4",
            name="Setup Database",
            priority="medium",
            status="todo",
            required_skill="database",
            remaining_effort=2.0,
            original_effort=2.0,
            dependencies=["task_2"],
            is_critical_path=False,
        ),
        TaskState(
            id="task_5",
            name="Integration Testing",
            priority="critical",
            status="todo",
            required_skill="testing",
            remaining_effort=2.0,
            original_effort=2.0,
            dependencies=["task_3", "task_4"],
            is_critical_path=True,
        ),
    ]


def get_risks() -> List[RiskState]:
    """No risks for the easy task."""
    return []
