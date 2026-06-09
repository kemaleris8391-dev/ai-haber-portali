import json
import os

path = r"C:\Users\Kaose\.gemini\antigravity-ide\brain\c3a68078-44e3-4595-afbf-2c958c61ab20\.system_generated\logs\transcript.jsonl"

if not os.path.exists(path):
    print("Transcript log file does not exist at", path)
else:
    print("Found transcript log file. Reading...")
    user_inputs = []
    model_responses = []
    
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                source = data.get("source")
                step_type = data.get("type")
                content = data.get("content", "")
                
                if source == "USER_EXPLICIT" or step_type == "USER_INPUT":
                    user_inputs.append((line_num, content))
                elif source == "MODEL":
                    # We can look for model responses
                    if "gemma" in content.lower() or "kategori" in content.lower():
                        model_responses.append((line_num, content))
            except Exception as e:
                print(f"Error parsing line {line_num}: {e}")
                
    print(f"\nTotal user messages: {len(user_inputs)}")
    print("User messages:")
    for idx, (ln, content) in enumerate(user_inputs):
        print(f"[{idx}] (Line {ln}): {content[:300]}...")
        if "cdc3846d4147" in content or "yoru" in content or "gemma" in content.lower():
            print(f"    --> FULL MATCHING CONTENT: {content}")
        print("-" * 40)
