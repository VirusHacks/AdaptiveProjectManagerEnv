"""
Quick test using the NEW container
"""

import asyncio
from client import AdaptiveProjectManagerClient
from models import ProjectAction, Assignment

async def quick_test():
    print("Starting new container from image...")
    
    # Start fresh container from the new image
    env = await AdaptiveProjectManagerClient.from_docker_image("adaptive-project-manager:latest")
    
    try:
        result = await env.reset(task_id="easy")
        obs = result.observation
        
        print(f"Connected! Running quick test...")
        print(f"Initial: day={obs.day}, tasks={len(obs.tasks)}, done={result.done}")
        
        #  Run to completion
        for i in range(20):
            if result.done:
                break
            
            # Simple assignment strategy
            assignments = []
            for emp in obs.employees:
                if not emp.available:
                    continue
                for task in obs.tasks:
                    if task.status in ["todo", "in_progress"] and task.required_skill in emp.skills:
                        assignments.append(Assignment(employee_id=emp.id, task_id=task.id))
                        break
            
            action = ProjectAction(assignments=assignments)
            result = await env.step(action)
            obs = result.observation
        
        if result.done:
            print(f"\nEpisode completed!")
            print(f"  Day: {obs.day}")
            print(f"  Done: {result.done}")
            print(f"  Completion: {obs.project_completion:.1%}")
            print(f"  Final Score (direct field): {obs.final_score}")
            print(f"  Metadata: {obs.metadata}")
            
            # Use direct field, fall back to metadata
            final_score = obs.final_score if obs.final_score is not None else obs.metadata.get("final_score", "NOT_FOUND")
            print(f"\n  FINAL SCORE: {final_score}")
        
        await env.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(quick_test())
