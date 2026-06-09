import re
import json

file_path = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\fetched_share_response.html"
output_path = r"C:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\scratch\final_share_parsed.txt"

with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

# Let's find all script blocks
# Usually, in a shared page, window.WIZ_global_data is populated.
# Let's search for "WIZ_global_data" and extract the entire JSON object
match = re.search(r'window\.WIZ_global_data\s*=\s*(\{.*?\});', html, re.DOTALL)
if match:
    try:
        wiz_data = json.loads(match.group(1))
        # Let's search inside the values of wiz_data for strings containing "Oyun" or "PLC" or "PC"
        with open(output_path, "w", encoding="utf-8") as out:
            for k, v in wiz_data.items():
                v_str = str(v)
                if "Oyun" in v_str or "PC" in v_str or "PLC" in v_str:
                    out.write(f"KEY: {k}\n")
                    # If it's a list, let's look through elements
                    if isinstance(v, list):
                        for item in v:
                            item_str = str(item)
                            if "Oyun" in item_str or "PC" in item_str:
                                out.write(json.dumps(item, ensure_ascii=False, indent=2) + "\n")
                    else:
                        out.write(v_str + "\n")
                    out.write("=" * 80 + "\n")
        print("Done parsing. Output written to final_share_parsed.txt")
    except Exception as e:
        print("JSON parse error:", e)
else:
    # If not found, look for all strings in quotes that contain Oyun or PC
    print("WIZ_global_data not found. Searching all quoted strings...")
    matches = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', html)
    found = []
    for m in matches:
        try:
            decoded = m.encode().decode('unicode-escape')
        except:
            decoded = m
        if "Oyun" in decoded or "PC" in decoded:
            found.append(decoded)
            
    with open(output_path, "w", encoding="utf-8") as out:
        for f in found:
            out.write(f + "\n\n")
    print(f"Done. Wrote {len(found)} quoted strings.")
