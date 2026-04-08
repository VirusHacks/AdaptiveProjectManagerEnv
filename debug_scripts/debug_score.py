"""
Debug script to trace why final_score is 0.
"""

import asyncio
from client import AdaptiveProjectManagerClient
from models import ProjectAction, Assignment

async def debug_scoring():
    """Debug the scoring issue step by step."""
    
    print("=" * 80)
    print("DEBUG: Final Score Investigation")
    print("=" * 80)
    
    env = await AdaptiveProjectManagerClient.from_docker_image("adaptive-project-manager:latest")
    
    try:
        result = await env.reset(task_id="easy")
        obs = result.observation
        
        print(f"\nInitial state:")
        print(f"  done: {result.done}")
        print(f"  metadata: {obs.metadata}")
        
        # Run just a few steps to complete quickly
        for i in range(15):
            if result.done:
                print(f"\n{'='*80}")
                print(f"EPISODE DONE at step {i}")
                print(f"{'='*80}")
                break
            
            # Simple strategy
            assignments = []
            available_tasks = [t for t in obs.tasks if t.status in ["todo", "in_progress"] and not t.dependencies]
            available_employees = [e for e in obs.employees if e.available]
            
            # Just assign first available employee to first available task
            for emp in available_employees[:2]:
                for task in available_tasks[:2]:
                    if task.required_skill in emp.skills:
                        assignments.append(Assignment(employee_id=emp.id, task_id=task.id))
                        available_tasks.remove(task)
                        break
            
            action = ProjectAction(assignments=assignments, contingency_action="none")
            result = await env.step(action)
            obs = result.observation
            
            completed = [t for t in obs.tasks if t.status == "done"]
            print(f"\nStep {i+1}: Day {obs.day}, done={result.done}, completed={len(completed)}/{len(obs.tasks)}")
            
            if result.done:
                print(f"\n{'='*80}")
                print(f"EPISODE DONE at step {i+1}")
                print(f"{'='*80}")
                print(f"  obs.done: {obs.done}")
                print(f"  result.done: {result.done}")
                print(f"  obs.metadata: {obs.metadata}")
                print(f"  obs.metadata type: {type(obs.metadata)}")
                
                final_score = obs.metadata.get("final_score", "NOT_FOUND")
                print(f"\n  Final score from metadata: {final_score}")
                
                # Check why it terminated
                print(f"\n  Termination reason:")
                print(f"    All tasks done: {all(t.status == 'done' for t in obs.tasks)}")
                print(f"    Deadline reached: {obs.day >= obs.day + obs.days_remaining}")
                print(f"    Budget exhausted: (can't check from client)")
                
                # Show task statuses
                print(f"\n  Task statuses:")
                for t in obs.tasks:
                    print(f"    {t.id}: {t.status}, critical={t.is_critical_path}")
                
                # Show final state
                print(f"\n  Final state:")
                print(f"    Day: {obs.day}")
                print(f"    Project completion: {obs.project_completion:.1%}")
                print(f"    Budget remaining: ${obs.budget_remaining:,.0f}")
                print(f"    Average burnout: {obs.average_burnout:.2f}")
                
                break
        
        if not result.done:
            print(f"\n⚠️  Episode did NOT complete in 15 steps")
        
        await env.close()
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_scoring())
