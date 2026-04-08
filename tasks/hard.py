# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Hard Task: Enterprise Migration Crisis

Seed: 9001
- 5 employees
- 14 tasks (+ dynamically added compliance task + production hotfix)
- 22 day limit (tight)
- Day 5: backend unavailable 3 days
- Day 7: production incident — urgent hotfix task injected
- Day 9: new compliance task added
- Day 12: vendor delay +3 effort
- Day 15: if burnout high, QA productivity halves
- Day 18: key person (Eve) unavailable 2 days
"""

from typing import Dict, Any, List
from models import TaskState, EmployeeState, RiskState


def get_hard_task() -> Dict[str, Any]:
    """
    Generate the hard task configuration: Enterprise Migration Crisis.
    
    A complex project with multiple disruptions and dynamic challenges.
    """
    return {
        "task_id": "hard",
        "name": "Enterprise Migration Crisis",
        "seed": 9001,
        "total_days": 22,
        "budget_total": 130000.0,
        "daily_burn_rate": 5000.0,
        "employees": get_employees(),
        "tasks": get_tasks(),
        "risks": get_risks(),
        "scheduled_events": get_scheduled_events(),
    }


def get_employees() -> List[EmployeeState]:
    """Create 5 employees for the hard task."""
    return [
        EmployeeState(
            id="emp_1",
            name="Alice",
            skills=["frontend", "ui_design", "documentation"],
            available=True,
            workload=0.0,
            burnout=0.0,
            productivity_modifier=1.0,
        ),
        EmployeeState(
            id="emp_2",
            name="Bob",
            skills=["backend", "api", "database"],
            available=True,
            workload=0.0,
            burnout=0.0,
            productivity_modifier=1.0,
        ),
        EmployeeState(
            id="emp_3",
            name="Carol",
            skills=["database", "migration", "backend"],
            available=True,
            workload=0.0,
            burnout=0.0,
            productivity_modifier=1.0,
        ),
        EmployeeState(
            id="emp_4",
            name="David",
            skills=["testing", "qa", "security"],
            available=True,
            workload=0.0,
            burnout=0.0,
            productivity_modifier=1.0,
        ),
        EmployeeState(
            id="emp_5",
            name="Eve",
            skills=["devops", "infrastructure", "security", "compliance"],
            available=True,
            workload=0.0,
            burnout=0.0,
            productivity_modifier=1.0,
        ),
    ]


def get_tasks() -> List[TaskState]:
    """Create 14 tasks for the hard task."""
    return [
        TaskState(
            id="task_1",
            name="Legacy System Analysis",
            priority="critical",
            status="todo",
            required_skill="backend",
            remaining_effort=3.0,
            original_effort=3.0,
            dependencies=[],
            is_critical_path=True,
        ),
        TaskState(
            id="task_2",
            name="Database Schema Design",
            priority="critical",
            status="todo",
            required_skill="database",
            remaining_effort=3.0,
            original_effort=3.0,
            dependencies=["task_1"],
            is_critical_path=True,
        ),
        TaskState(
            id="task_3",
            name="Infrastructure Setup",
            priority="high",
            status="todo",
            required_skill="infrastructure",
            remaining_effort=2.0,
            original_effort=2.0,
            dependencies=[],
            is_critical_path=True,
        ),
        TaskState(
            id="task_4",
            name="API Gateway Design",
            priority="high",
            status="todo",
            required_skill="api",
            remaining_effort=2.0,
            original_effort=2.0,
            dependencies=["task_1"],
            is_critical_path=True,
        ),
        TaskState(
            id="task_5",
            name="Data Migration Scripts",
            priority="critical",
            status="todo",
            required_skill="migration",
            remaining_effort=4.0,
            original_effort=4.0,
            dependencies=["task_2"],
            is_critical_path=True,
        ),
        TaskState(
            id="task_6",
            name="Backend Core Services",
            priority="critical",
            status="todo",
            required_skill="backend",
            remaining_effort=5.0,
            original_effort=5.0,
            dependencies=["task_2", "task_4"],
            is_critical_path=True,
        ),
        TaskState(
            id="task_7",
            name="Frontend Migration",
            priority="high",
            status="todo",
            required_skill="frontend",
            remaining_effort=4.0,
            original_effort=4.0,
            dependencies=["task_4"],
            is_critical_path=False,
        ),
        TaskState(
            id="task_8",
            name="Build Auth System (In-House)",
            priority="critical",
            status="todo",
            required_skill="security",
            remaining_effort=8.0,
            original_effort=8.0,
            dependencies=["task_6"],
            is_critical_path=True,
            mutually_exclusive_with="task_15",
            fixed_cost=0.0,
        ),
        TaskState(
            id="task_9",
            name="Vendor Integration",
            priority="high",
            status="todo",
            required_skill="api",
            remaining_effort=3.0,
            original_effort=3.0,
            dependencies=["task_6"],
            is_critical_path=True,
        ),
        TaskState(
            id="task_10",
            name="Performance Testing",
            priority="high",
            status="todo",
            required_skill="testing",
            remaining_effort=2.0,
            original_effort=2.0,
            dependencies=["task_5", "task_6"],
            is_critical_path=False,
        ),
        TaskState(
            id="task_11",
            name="QA Testing Suite",
            priority="critical",
            status="todo",
            required_skill="qa",
            remaining_effort=4.0,
            original_effort=4.0,
            dependencies=["task_6", "task_7", "task_8", "task_15"],
            is_critical_path=True,
        ),
        TaskState(
            id="task_12",
            name="DevOps Pipeline",
            priority="medium",
            status="todo",
            required_skill="devops",
            remaining_effort=2.0,
            original_effort=2.0,
            dependencies=["task_3"],
            is_critical_path=False,
        ),
        TaskState(
            id="task_13",
            name="User Documentation",
            priority="low",
            status="todo",
            required_skill="documentation",
            remaining_effort=2.0,
            original_effort=2.0,
            dependencies=["task_7"],
            is_critical_path=False,
        ),
        TaskState(
            id="task_14",
            name="Final Integration",
            priority="critical",
            status="todo",
            required_skill="backend",
            remaining_effort=3.0,
            original_effort=3.0,
            dependencies=["task_9", "task_10", "task_11", "task_12"],
            is_critical_path=True,
        ),
        TaskState(
            id="task_15",
            name="Buy Auth API (Vendor)",
            priority="critical",
            status="todo",
            required_skill="api",
            remaining_effort=1.0,
            original_effort=1.0,
            dependencies=["task_6"],
            is_critical_path=True,
            mutually_exclusive_with="task_8",
            fixed_cost=15000.0,
        ),
    ]


def get_risks() -> List[RiskState]:
    """Define risks for the hard task."""
    return [
        RiskState(
            id="risk_1",
            name="Backend developer emergency leave",
            probability=1.0,
            impact="Backend employee unavailable for 3 days",
            triggered=False,
            trigger_day=5,
        ),
        RiskState(
            id="risk_2",
            name="New compliance requirement",
            probability=1.0,
            impact="New compliance task must be added",
            triggered=False,
            trigger_day=9,
        ),
        RiskState(
            id="risk_3",
            name="Vendor API delay",
            probability=1.0,
            impact="Vendor integration task +3 effort",
            triggered=False,
            trigger_day=12,
        ),
        RiskState(
            id="risk_4",
            name="Team burnout impact",
            probability=1.0,
            impact="If average burnout > 0.6, QA productivity halves",
            triggered=False,
            trigger_day=15,
        ),
        RiskState(
            id="risk_5",
            name="Production incident",
            probability=1.0,
            impact="Urgent hotfix required within 3 days",
            triggered=False,
            trigger_day=7,
        ),
        RiskState(
            id="risk_6",
            name="Key person risk",
            probability=1.0,
            impact="DevOps lead poached, unavailable 2 days",
            triggered=False,
            trigger_day=18,
        ),
    ]


def get_scheduled_events() -> List[Dict[str, Any]]:
    """Define scheduled events for the hard task."""
    return [
        {
            "day": 5,
            "type": "employee_unavailable",
            "employee_id": "emp_2",
            "duration": 3,
            "message": "Bob has an emergency and is unavailable for 3 days",
        },
        {
            "day": 9,
            "type": "add_task",
            "task": TaskState(
                id="task_15",
                name="Compliance Audit",
                priority="critical",
                status="todo",
                required_skill="compliance",
                remaining_effort=3.0,
                original_effort=3.0,
                dependencies=["task_8"],
                is_critical_path=True,
            ).model_dump(),
            "message": "New compliance requirement: Compliance Audit task added",
        },
        {
            "day": 7,
            "type": "add_task",
            "task": TaskState(
                id="task_16",
                name="Production Hotfix",
                priority="critical",
                status="todo",
                required_skill="backend",
                remaining_effort=2.0,
                original_effort=2.0,
                dependencies=[],
                is_critical_path=True,
                deadline_day=10,  # Must complete within 3 days
            ).model_dump(),
            "message": "PRODUCTION INCIDENT: Critical hotfix needed. Must complete within 3 days or stakeholder impact.",
        },
        {
            "day": 12,
            "type": "task_effort_increase",
            "task_id": "task_9",
            "effort_increase": 3.0,
            "message": "Vendor API has breaking changes (+3 effort for integration)",
        },
        {
            "day": 15,
            "type": "burnout_check",
            "threshold": 0.6,
            "affected_skills": ["qa", "testing"],
            "productivity_penalty": 0.5,
            "message": "High team burnout is affecting QA productivity",
        },
        {
            "day": 18,
            "type": "employee_unavailable",
            "employee_id": "emp_5",
            "duration": 2,
            "message": "Eve has been poached by a competitor and is unavailable for 2 days while negotiating retention",
        },
    ]
