import json
import os

path = r"C:\Users\Kaose\.gemini\antigravity-ide\brain\c3a68078-44e3-4595-afbf-2c958c61ab20\.system_generated\logs\transcript.jsonl"

if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        try:
            data = json.loads(line)
            content = data.get("content", "")
            if "cdc3846d4147" in content:
                print(f"--- USER REQUEST AT LINE {i} ---")
                print(content[:500])
                print("\n--- MODEL RESPONSES FOLLOWING THIS REQUEST ---")
                # Look at the next few lines
                for j in range(i+1, min(len(lines), i+10)):
                    next_data = json.loads(lines[j])
                    if next_data.get("source") == "MODEL":
                        print(f"[Step {j}] MODEL CONTENT:")
                        print(next_data.get("content", "")[:2000])
                        print("=" * 60)
        except Exception as e:
            pass
