"""
Test the grading function directly to understand the 0.0 score issue.
"""

import asyncio
from client import AdaptiveProjectManagerClient
from graders.base_grader import (
    compute_final_score,
    _compute_completion_score,
    _compute_deadline_score,
    _compute_budget_score,
    _compute_team_health_score,
)
from models import ProjectAction, Assignment

async def test_grading():
    """Test grading on a completed project."""
    
    print("=" * 80)
    print("GRADING TEST")
    print("=" * 80)
    
    env = await AdaptiveProjectManagerClient.from_docker_image("adaptive-project-manager:latest")
    
    try:
        result = await env.reset(task_id="easy")
        
        # Run to completion
        max_steps = 20
        for i in range(max_steps):
            if result.done:
                break
            
            obs = result.observation
            
            # Simple strategy: assign available employees to available tasks
            assignments = []
            available_tasks = [t for t in obs.tasks if t.status in ["todo", "in_progress"]]
            available_employees = [e for e in obs.employees if e.available]
            
            # Match employees to tasks by skill
            for emp in available_employees[:3]:
                for task in available_tasks:
                    if task.required_skill in emp.skills and not any(a.task_id == task.id for a in assignments):
                        assignments.append(Assignment(employee_id=emp.id, task_id=task.id))
                        break
            
            action = ProjectAction(assignments=assignments, contingency_action="none")
            result = await env.step(action)
        
        # Get the project state
        project_state = env.get_project_state()
        
        print(f"\nProject State at End:")
        print(f"  Day: {project_state.day}")
        print(f"  Total days: {project_state.total_days}")
        print(f"  Budget total: ${project_state.budget_total:,.0f}")
        print(f"  Budget spent: ${project_state.budget_spent:,.0f}")
        print(f"  Stakeholder satisfaction: {project_state.stakeholder_satisfaction:.2f}")
        
        print(f"\nTasks:")
        for task in project_state.tasks:
            print(f"  {task.id}: {task.status}, priority={task.priority}, critical={task.is_critical_path}")
        
        print(f"\nEmployees:")
        for emp in project_state.employees:
            print(f"  {emp.id}: burnout={emp.burnout:.2f}")
        
        # Compute score components manually
        print(f"\n" + "=" * 80)
        print("SCORE COMPONENTS")
        print("=" * 80)
        
        completion_score = _compute_completion_score(project_state)
        print(f"\n1. Completion Score: {completion_score:.4f}")
        print(f"   (35% weight)")
        
        completed = sum(1 for t in project_state.tasks if t.status == "done")
        print(f"   Completed: {completed}/{len(project_state.tasks)}")
        
        deadline_score = _compute_deadline_score(project_state)
        print(f"\n2. Deadline Score: {deadline_score:.4f}")
        print(f"   (25% weight)")
        
        days_remaining = project_state.total_days - project_state.day
        print(f"   Days remaining: {days_remaining}")
        critical_tasks = [t for t in project_state.tasks if t.is_critical_path]
        critical_done = all(t.status == "done" for t in critical_tasks)
        print(f"   All critical tasks done: {critical_done}")
        print(f"   Critical tasks: {[t.id for t in critical_tasks]}")
        print(f"   Critical task statuses: {[(t.id, t.status) for t in critical_tasks]}")
        
        budget_score = _compute_budget_score(project_state)
        print(f"\n3. Budget Score: {budget_score:.4f}")
        print(f"   (15% weight)")
        print(f"   Budget remaining: ${project_state.budget_total - project_state.budget_spent:,.0f}")
        
        team_health_score = _compute_team_health_score(project_state)
        print(f"\n4. Team Health Score: {team_health_score:.4f}")
        print(f"   (15% weight)")
        avg_burnout = sum(e.burnout for e in project_state.employees) / len(project_state.employees)
        print(f"   Average burnout: {avg_burnout:.2f}")
        
        stakeholder_score = project_state.stakeholder_satisfaction
        print(f"\n5. Stakeholder Score: {stakeholder_score:.4f}")
        print(f"   (10% weight)")
        
        # Compute final score
        print(f"\n" + "=" * 80)
        print("FINAL SCORE CALCULATION")
        print("=" * 80)
        
        final_score = compute_final_score(project_state)
        
        print(f"\nFinal Score = (")
        print(f"    0.35 * {completion_score:.4f}")
        print(f"  + 0.25 * {deadline_score:.4f}")
        print(f"  + 0.15 * {budget_score:.4f}")
        print(f"  + 0.15 * {team_health_score:.4f}")
        print(f"  + 0.10 * {stakeholder_score:.4f}")
        print(f") = {final_score:.4f}")
        
        manual_calc = (
            0.35 * completion_score
            + 0.25 * deadline_score
            + 0.15 * budget_score
            + 0.15 * team_health_score
            + 0.10 * stakeholder_score
        )
        print(f"\nManual calculation: {manual_calc:.4f}")
        
        # Now check what the environment returned
        if result.done:
            obs = result.observation
            env_score = obs.metadata.get("final_score", 0.0)
            print(f"Environment returned score: {env_score:.4f}")
            
            if abs(env_score - final_score) > 0.0001:
                print(f"\n⚠️  MISMATCH! Environment score ({env_score:.4f}) != Computed score ({final_score:.4f})")
            else:
                print(f"\n✅ Scores match!")
        
        await env.close()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_grading())
