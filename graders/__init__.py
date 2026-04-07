# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Grader modules for the Adaptive Project Manager Environment."""

from .base_grader import compute_final_score
from .easy_grader import grade_easy
from .medium_grader import grade_medium
from .hard_grader import grade_hard

GRADER_REGISTRY = {
    "easy": grade_easy,
    "small_web_launch": grade_easy,
    "medium": grade_medium,
    "startup_mvp_crunch": grade_medium,
    "hard": grade_hard,
    "enterprise_migration_crisis": grade_hard,
}

__all__ = ["GRADER_REGISTRY", "compute_final_score", "grade_easy", "grade_medium", "grade_hard"]
