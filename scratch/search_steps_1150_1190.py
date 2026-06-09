import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

path = r"C:\Users\Kaose\.gemini\antigravity-ide\brain\c3a68078-44e3-4595-afbf-2c958c61ab20\.system_generated\logs\transcript.jsonl"

if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    start = 1150
    end = min(len(lines), 1190)
    for idx in range(start, end):
        try:
            data = json.loads(lines[idx])
            source = data.get("source")
            step_type = data.get("type")
            content = data.get("content", "")
            safe_content = content.encode('ascii', 'replace').decode('ascii')
            print(f"--- STEP {idx} | Source: {source} | Type: {step_type} ---")
            print(safe_content[:3000])
            print("*" * 80)
        except Exception as e:
            print(f"Error printing line {idx}: {e}")
else:
    print("Transcript log file does not exist.")
