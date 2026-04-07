# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Hard Task Grader: Enterprise Migration Crisis

Deterministic grader for the hard task.
"""

from typing import TYPE_CHECKING
from .base_grader import compute_final_score

if TYPE_CHECKING:
    from models import ProjectState


def grade_hard(state: "ProjectState") -> float:
    """
    Grade the hard task.
    
    The hard task has multiple disruptions and requires effective crisis management.
    
    Args:
        state: Final project state
        
    Returns:
        Score in [0.0, 1.0]
    """
    base_score = compute_final_score(state)
    
    # Check if compliance task was completed (added dynamically on day 9)
    compliance_task = next((t for t in state.tasks if t.id == "task_15"), None)
    if compliance_task and compliance_task.status == "done":
        # Bonus for handling the compliance requirement
        base_score = min(1.0, base_score + 0.03)
    
    # Check if vendor integration was completed despite delay
    vendor_task = next((t for t in state.tasks if t.id == "task_9"), None)
    if vendor_task and vendor_task.status == "done":
        # Bonus for handling vendor delay
        base_score = min(1.0, base_score + 0.02)
    
    # Penalty for high average burnout at end
    avg_burnout = sum(e.burnout for e in state.employees) / len(state.employees) if state.employees else 0
    if avg_burnout > 0.7:
        # Heavy penalty for burning out the team
        base_score = max(0.0, base_score - 0.1)
    
    return max(0.0, min(1.0, base_score))
