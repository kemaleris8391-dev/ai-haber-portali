import re

path = r"c:\Users\Kaose\AndroidStudioProjects\ai-haber-portali\web-portal\api\webhook.py"

with open(path, "r", encoding="utf-8") as f:
    code = f.readlines()

# Let's find all function definitions
funcs = []
for i, line in enumerate(code, 1):
    if line.startswith("def "):
        funcs.append((i, line.strip()))

print(f"Found {len(funcs)} functions:")
for idx, (ln, f) in enumerate(funcs):
    print(f"[{idx}] (Line {ln}): {f}")
