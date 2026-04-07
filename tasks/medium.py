# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Medium Task: Startup MVP Crunch

Seed: 1337
- 4 employees
- 9 tasks
- 18 day limit
- Day 6: backend employee unavailable for 2 days
- Day 10: payment task +2 effort
"""

from typing import Dict, Any, List
from models import TaskState, EmployeeState, RiskState


def get_medium_task() -> Dict[str, Any]:
    """
    Generate the medium task configuration: Startup MVP Crunch.
    
    A more complex project with scheduled disruptions.
    """
    return {
        "task_id": "medium",
        "name": "Startup MVP Crunch",
        "seed": 1337,
        "total_days": 18,
        "budget_total": 80000.0,
        "daily_burn_rate": 3000.0,
        "employees": get_employees(),
        "tasks": get_tasks(),
        "risks": get_risks(),
        "scheduled_events": get_scheduled_events(),
    }


def get_employees() -> List[EmployeeState]:
    """Create 4 employees for the medium task."""
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
            skills=["backend", "api"],
            available=True,
            workload=0.0,
            burnout=0.0,
            productivity_modifier=1.0,
        ),
        EmployeeState(
            id="emp_3",
            name="Carol",
            skills=["database", "backend"],
            available=True,
            workload=0.0,
            burnout=0.0,
            productivity_modifier=1.0,
        ),
        EmployeeState(
            id="emp_4",
            name="David",
            skills=["testing", "security", "frontend"],
            available=True,
            workload=0.0,
            burnout=0.0,
            productivity_modifier=1.0,
        ),
    ]


def get_tasks() -> List[TaskState]:
    """Create 9 tasks for the medium task."""
    return [
        TaskState(
            id="task_1",
            name="Design User Interface",
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
            name="Setup Core API",
            priority="high",
            status="todo",
            required_skill="api",
            remaining_effort=3.0,
            original_effort=3.0,
            dependencies=[],
            is_critical_path=True,
        ),
        TaskState(
            id="task_3",
            name="Database Schema",
            priority="high",
            status="todo",
            required_skill="database",
            remaining_effort=2.0,
            original_effort=2.0,
            dependencies=[],
            is_critical_path=True,
        ),
        TaskState(
            id="task_4",
            name="User Authentication",
            priority="critical",
            status="todo",
            required_skill="backend",
            remaining_effort=3.0,
            original_effort=3.0,
            dependencies=["task_2", "task_3"],
            is_critical_path=True,
        ),
        TaskState(
            id="task_5",
            name="Frontend Implementation",
            priority="high",
            status="todo",
            required_skill="frontend",
            remaining_effort=4.0,
            original_effort=4.0,
            dependencies=["task_1"],
            is_critical_path=True,
        ),
        TaskState(
            id="task_6",
            name="Payment Integration",
            priority="critical",
            status="todo",
            required_skill="api",
            remaining_effort=3.0,
            original_effort=3.0,
            dependencies=["task_4"],
            is_critical_path=True,
        ),
        TaskState(
            id="task_7",
            name="Security Audit",
            priority="medium",
            status="todo",
            required_skill="security",
            remaining_effort=2.0,
            original_effort=2.0,
            dependencies=["task_4", "task_6"],
            is_critical_path=False,
        ),
        TaskState(
            id="task_8",
            name="Integration Testing",
            priority="critical",
            status="todo",
            required_skill="testing",
            remaining_effort=3.0,
            original_effort=3.0,
            dependencies=["task_5", "task_6"],
            is_critical_path=True,
        ),
        TaskState(
            id="task_9",
            name="Documentation",
            priority="low",
            status="todo",
            required_skill="frontend",
            remaining_effort=1.0,
            original_effort=1.0,
            dependencies=["task_8"],
            is_critical_path=False,
        ),
    ]


def get_risks() -> List[RiskState]:
    """Define risks for the medium task."""
    return [
        RiskState(
            id="risk_1",
            name="Backend developer illness",
            probability=1.0,  # Deterministic for testing
            impact="Backend employee unavailable for 2 days",
            triggered=False,
            trigger_day=6,
        ),
        RiskState(
            id="risk_2",
            name="Payment API complexity",
            probability=1.0,
            impact="Payment task requires +2 additional effort",
            triggered=False,
            trigger_day=10,
        ),
    ]


def get_scheduled_events() -> List[Dict[str, Any]]:
    """Define scheduled events for the medium task."""
    return [
        {
            "day": 6,
            "type": "employee_unavailable",
            "employee_id": "emp_2",
            "duration": 2,
            "message": "Bob is sick and unavailable for 2 days",
        },
        {
            "day": 10,
            "type": "task_effort_increase",
            "task_id": "task_6",
            "effort_increase": 2.0,
            "message": "Payment integration is more complex than expected (+2 effort)",
        },
    ]
