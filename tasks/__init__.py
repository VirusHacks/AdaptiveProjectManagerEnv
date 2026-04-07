# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Task definitions for the Adaptive Project Manager Environment."""

from .easy import get_easy_task
from .medium import get_medium_task
from .hard import get_hard_task

TASK_REGISTRY = {
    "easy": get_easy_task,
    "small_web_launch": get_easy_task,
    "medium": get_medium_task,
    "startup_mvp_crunch": get_medium_task,
    "hard": get_hard_task,
    "enterprise_migration_crisis": get_hard_task,
}

__all__ = ["TASK_REGISTRY", "get_easy_task", "get_medium_task", "get_hard_task"]
