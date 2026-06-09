import json
import os

path = r"C:\Users\Kaose\.gemini\antigravity-ide\brain\c3a68078-44e3-4595-afbf-2c958c61ab20\.system_generated\logs\transcript.jsonl"

if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    found_idx = -1
    for i, line in enumerate(lines):
        if "cdc3846d4147" in line:
            found_idx = i
            break
            
    if found_idx != -1:
        print(f"Found cdc3846d4147 at line {found_idx}")
        # Print lines around it
        start = max(0, found_idx - 2)
        end = min(len(lines), found_idx + 10)
        for idx in range(start, end):
            try:
                data = json.loads(lines[idx])
                source = data.get("source")
                step_type = data.get("type")
                content = data.get("content", "")
                print(f"--- STEP {idx} | Source: {source} | Type: {step_type} ---")
                print(content[:2500])
                print("*" * 80)
            except Exception as e:
                print(f"Error parsing line {idx}: {e}")
    else:
        print("Not found cdc3846d4147 in transcript.")
