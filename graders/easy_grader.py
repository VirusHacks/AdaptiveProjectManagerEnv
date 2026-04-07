# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Easy Task Grader: Small Web Launch

Deterministic grader for the easy task.
"""

from typing import TYPE_CHECKING
from .base_grader import compute_final_score

if TYPE_CHECKING:
    from models import ProjectState


def grade_easy(state: "ProjectState") -> float:
    """
    Grade the easy task.
    
    The easy task has no special considerations - just use the base grader.
    
    Args:
        state: Final project state
        
    Returns:
        Score in [0.0, 1.0]
    """
    return compute_final_score(state)
