# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Hard Task Grader: Enterprise Migration Crisis

Deterministic grader for the hard task.
Accounts for: compliance audit, vendor delay, production hotfix, key person risk.
"""

from typing import TYPE_CHECKING
from .base_grader import compute_final_score

if TYPE_CHECKING:
    from models import ProjectState


def grade_hard(state: "ProjectState") -> float:
    """
    Grade the hard task.
    
    The hard task has 6 disruptions across 22 days and requires effective
    crisis management, long-horizon planning, and burnout control.
    
    Args:
        state: Final project state
        
    Returns:
        Score in [0.0, 1.0]
    """
    base_score = compute_final_score(state)
    
    # Bonus: completed the dynamically-added compliance task (day 9)
    compliance_task = next((t for t in state.tasks if t.id == "task_15"), None)
    if compliance_task and compliance_task.status == "done":
        base_score = min(1.0, base_score + 0.03)
    
    # Bonus: completed vendor integration despite +3 effort delay (day 12)
    vendor_task = next((t for t in state.tasks if t.id == "task_9"), None)
    if vendor_task and vendor_task.status == "done":
        base_score = min(1.0, base_score + 0.02)
    
    # Bonus/Penalty: production hotfix (day 7, deadline day 10)
    hotfix_task = next((t for t in state.tasks if t.id == "task_16"), None)
    if hotfix_task:
        if hotfix_task.status == "done":
            # Bonus for handling the production incident
            base_score = min(1.0, base_score + 0.03)
        else:
            # Penalty for failing to resolve production incident
            base_score = max(0.0, base_score - 0.08)
    
    # Penalty for high average burnout at end (threshold 0.6, stricter than before)
    avg_burnout = sum(e.burnout for e in state.employees) / len(state.employees) if state.employees else 0
    if avg_burnout > 0.6:
        # Graduated penalty: burns harder as burnout climbs
        penalty = (avg_burnout - 0.6) * 0.25
        base_score = max(0.0, base_score - penalty)
    
    return max(0.0, min(1.0, base_score))
