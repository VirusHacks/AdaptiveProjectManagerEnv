
import re
import json
import os
from pathlib import Path

def test_output_parsing(file_path):
    print(f"--- Testing Output Parsing on {file_path} ---")
    content = Path(file_path).read_text(encoding='utf-8')
    
    start_pattern = r"\[START\] task=([\w\-]+)"
    step_pattern = r"\[STEP\] day=(\d+) action=(\{.*?\}) reward=([\-\d\.]+)"
    end_pattern = r"\[END\] task=([\w\-]+) score=([\d\.]+)"
    
    starts = re.findall(start_pattern, content)
    steps = re.findall(step_pattern, content)
    ends = re.findall(end_pattern, content)
    
    print(f"Found {len(starts)} [START] tags: {starts}")
    print(f"Found {len(steps)} [STEP] tags")
    print(f"Found {len(ends)} [END] tags: {ends}")
    
    if len(starts) == 0:
        print("[FAIL] No [START] tags found")
    if len(steps) == 0:
        print("[FAIL] No [STEP] tags found")
    if len(ends) == 0:
        print("[FAIL] No [END] tags found")
        
    # Verify JSON in steps
    for day, action_json, reward in steps:
        try:
            json.loads(action_json)
        except Exception as e:
            print(f"[FAIL] Invalid JSON in step day {day}: {e}")
            return False
            
    if len(starts) == len(ends) and len(starts) > 0:
        print("[PASS] Output Parsing structure looks correct")
        return True
    else:
        print("[FAIL] Mismatch between START and END tags")
        return False

def test_task_validation():
    print("--- Testing Task Validation ---")
    try:
        from tasks import TASK_REGISTRY
        required = ["easy", "medium", "hard"]
        found = list(TASK_REGISTRY.keys())
        missing = [r for r in required if r not in found]
        if missing:
            print(f"[FAIL] Missing required tasks in registry: {missing}")
            return False
        else:
            print(f"[PASS] TASK_REGISTRY contains: {found}")
            return True
    except Exception as e:
        print(f"[FAIL] Could not import TASK_REGISTRY: {e}")
        return False

if __name__ == "__main__":
    p1 = test_task_validation()
    output_file = "validation_output.txt"
    if os.path.exists(output_file):
        p2 = test_output_parsing(output_file)
    else:
        print(f"[SKIP] {output_file} not found. Run inference first.")
        p2 = False
        
    if p1 and p2:
        print("\n[SUCCESS] Local verification PASSED. Ready for submission.")
    else:
        print("\n[FAILURE] Local verification failed some checks.")
