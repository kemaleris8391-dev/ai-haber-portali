import re
import json

file_path = r"C:\Users\Kaose\.gemini\antigravity-ide\brain\c3a68078-44e3-4595-afbf-2c958c61ab20\.system_generated\steps\1580\content.md"
output_path = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\current_share_wiz.txt"

with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# Look for WIZ_global_data = { ... }
match = re.search(r'window\.WIZ_global_data\s*=\s*(\{.*?\});', html, re.DOTALL)
if match:
    try:
        wiz_data = json.loads(match.group(1))
        # Write keys and values of interest
        with open(output_path, "w", encoding="utf-8") as out:
            for k, v in wiz_data.items():
                out.write(f"KEY: {k}\n")
                if isinstance(v, str):
                    out.write(v + "\n")
                else:
                    out.write(json.dumps(v, ensure_ascii=False, indent=2) + "\n")
                out.write("=" * 80 + "\n")
        print("Successfully wrote WIZ_global_data.")
    except Exception as e:
        print("JSON parse error:", e)
else:
    print("WIZ_global_data not found via regex.")
