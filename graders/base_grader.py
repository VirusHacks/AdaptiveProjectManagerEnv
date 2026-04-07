# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Base grader logic for the Adaptive Project Manager Environment.

Final score formula:
    score = (
        0.35 * completion_score
        + 0.25 * deadline_score
        + 0.15 * budget_score
        + 0.15 * team_health_score
        + 0.10 * stakeholder_satisfaction
    )
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import ProjectState


def compute_final_score(state: "ProjectState") -> float:
    """
    Compute the final score for a completed project.
    
    Args:
        state: The final ProjectState
        
    Returns:
        Score in [0.0, 1.0]
    """
    # 1. Completion score (35%)
    # Based on fraction of tasks completed, weighted by priority
    completion_score = _compute_completion_score(state)
    
    # 2. Deadline score (25%)
    # Based on whether project finished on time
    deadline_score = _compute_deadline_score(state)
    
    # 3. Budget score (15%)
    # Based on remaining budget
    budget_score = _compute_budget_score(state)
    
    # 4. Team health score (15%)
    # Based on average burnout levels
    team_health_score = _compute_team_health_score(state)
    
    # 5. Stakeholder satisfaction (10%)
    # Based on meeting critical path milestones
    stakeholder_score = state.stakeholder_satisfaction
    
    # Combine scores
    final_score = (
        0.35 * completion_score
        + 0.25 * deadline_score
        + 0.15 * budget_score
        + 0.15 * team_health_score
        + 0.10 * stakeholder_score
    )
    
    # Clamp to [0, 1]
    return max(0.0, min(1.0, final_score))


def _compute_completion_score(state: "ProjectState") -> float:
    """Compute task completion score weighted by priority."""
    if not state.tasks:
        return 0.0
    
    priority_weights = {
        "critical": 4.0,
        "high": 3.0,
        "medium": 2.0,
        "low": 1.0,
    }
    
    total_weight = 0.0
    completed_weight = 0.0
    
    for task in state.tasks:
        weight = priority_weights.get(task.priority, 1.0)
        total_weight += weight
        if task.status == "done":
            completed_weight += weight
    
    if total_weight == 0:
        return 0.0
    
    return completed_weight / total_weight


def _compute_deadline_score(state: "ProjectState") -> float:
    """Compute deadline score based on project completion time."""
    days_remaining = state.total_days - state.day
    
    # All critical tasks must be done for full deadline score
    critical_tasks = [t for t in state.tasks if t.is_critical_path]
    critical_done = all(t.status == "done" for t in critical_tasks)
    
    if not critical_done:
        # Penalty for not completing critical path
        return 0.0
    
    if days_remaining >= 0:
        # Finished on time - bonus for finishing early
        early_bonus = min(days_remaining / state.total_days, 0.2)
        return 0.8 + early_bonus
    else:
        # Late - penalty proportional to delay
        days_over = abs(days_remaining)
        penalty = min(days_over / 5, 1.0)  # Max penalty after 5 days late
        return max(0.0, 0.8 - penalty * 0.8)


def _compute_budget_score(state: "ProjectState") -> float:
    """Compute budget score based on spending."""
    if state.budget_total <= 0:
        return 0.0
    
    budget_remaining = state.budget_total - state.budget_spent
    budget_ratio = budget_remaining / state.budget_total
    
    if budget_remaining >= 0:
        # Under budget - full score with bonus for savings
        return 0.7 + min(budget_ratio * 0.3, 0.3)
    else:
        # Over budget - penalty
        over_ratio = abs(budget_remaining) / state.budget_total
        return max(0.0, 0.7 - over_ratio)


def _compute_team_health_score(state: "ProjectState") -> float:
    """Compute team health score based on burnout levels."""
    if not state.employees:
        return 1.0
    
    avg_burnout = sum(e.burnout for e in state.employees) / len(state.employees)
    
    # Lower burnout = higher score
    # 0 burnout = 1.0 score
    # 1.0 burnout = 0.0 score
    return max(0.0, 1.0 - avg_burnout)
