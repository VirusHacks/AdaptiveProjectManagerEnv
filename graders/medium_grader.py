# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Medium Task Grader: Startup MVP Crunch

Deterministic grader for the medium task.
"""

from typing import TYPE_CHECKING
from .base_grader import compute_final_score

if TYPE_CHECKING:
    from models import ProjectState


def grade_medium(state: "ProjectState") -> float:
    """
    Grade the medium task.
    
    The medium task uses base grading with consideration for
    handling disruptions effectively.
    
    Args:
        state: Final project state
        
    Returns:
        Score in [0.0, 1.0]
    """
    base_score = compute_final_score(state)
    
    # Check if payment integration (critical task) was completed despite difficulties
    payment_task = next((t for t in state.tasks if t.id == "task_6"), None)
    if payment_task and payment_task.status == "done":
        # Bonus for handling the payment complexity event
        base_score = min(1.0, base_score + 0.05)
    
    return max(0.0, min(1.0, base_score))
