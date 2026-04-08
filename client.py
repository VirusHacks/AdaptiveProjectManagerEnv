# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Adaptive Project Manager Environment Client."""

from typing import Dict, List

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import (
        ProjectAction, ProjectObservation, Assignment,
        TaskState, EmployeeState, RiskState,
    )
except ImportError:
    from models import (
        ProjectAction, ProjectObservation, Assignment,
        TaskState, EmployeeState, RiskState,
    )


class AdaptiveProjectManagerClient(
    EnvClient[ProjectAction, ProjectObservation, State]
):
    """
    Client for the Adaptive Project Manager Environment.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions with lower latency.
    Each client instance has its own dedicated environment session on the server.

    Example:
        >>> # Connect to a running server
        >>> with AdaptiveProjectManagerClient(base_url="http://localhost:8000") as client:
        ...     result = client.reset(task_id="easy")
        ...     print(f"Day {result.observation.day}, {result.observation.days_remaining} days remaining")
        ...
        ...     action = ProjectAction(
        ...         assignments=[Assignment(employee_id="emp_1", task_id="task_1")]
        ...     )
        ...     result = client.step(action)

    Example with Docker:
        >>> # Automatically start container and connect
        >>> client = AdaptiveProjectManagerClient.from_docker_image("adaptive-project-manager:latest")
        >>> try:
        ...     result = client.reset(task_id="easy")
        ...     result = client.step(ProjectAction(assignments=[]))
        ... finally:
        ...     client.close()
    """

    def _step_payload(self, action: ProjectAction) -> Dict:
        """
        Convert ProjectAction to JSON payload for step message.

        Args:
            action: ProjectAction instance

        Returns:
            Dictionary representation suitable for JSON encoding
        """
        # Use Pydantic's model_dump to ensure proper serialization
        # This includes the metadata field from the Action base class
        return action.model_dump()

    def _parse_result(self, payload: Dict) -> StepResult[ProjectObservation]:
        """
        Parse server response into StepResult[ProjectObservation].

        Args:
            payload: JSON response data from server

        Returns:
            StepResult with ProjectObservation
        """
        obs_data = payload.get("observation", {})
        
        # Parse tasks
        tasks = [
            TaskState(**t) for t in obs_data.get("tasks", [])
        ]
        
        # Parse employees
        employees = [
            EmployeeState(**e) for e in obs_data.get("employees", [])
        ]
        
        # Parse risks
        risks = [
            RiskState(**r) for r in obs_data.get("risks", [])
        ]
        
        observation = ProjectObservation(
            day=obs_data.get("day", 1),
            days_remaining=obs_data.get("days_remaining", 0),
            budget_remaining=obs_data.get("budget_remaining", 0.0),
            project_completion=obs_data.get("project_completion", 0.0),
            blocked_tasks=obs_data.get("blocked_tasks", 0),
            overdue_tasks=obs_data.get("overdue_tasks", 0),
            average_burnout=obs_data.get("average_burnout", 0.0),
            tasks=tasks,
            employees=employees,
            risks=risks,
            message=obs_data.get("message", ""),
            critical_path_progress=obs_data.get("critical_path_progress", 0.0),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
            final_score=obs_data.get("final_score"),  # Direct field for final score
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """
        Parse server response into State object.

        Args:
            payload: JSON response from state request

        Returns:
            State object with episode_id and step_count
        """
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )


# Legacy alias
HustlersEnv = AdaptiveProjectManagerClient
