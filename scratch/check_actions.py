import requests
import json

owner = "kemaleris8391-dev"
repo = "ai-haber-portali"
url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"

try:
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    print("Status Code:", response.status_code)
    if response.status_code == 200:
        data = response.json()
        runs = data.get("workflow_runs", [])
        print(f"Found {len(runs)} runs:")
        for run in runs[:10]:
            print(f"- Run #{run['run_number']}: event={run['event']}, status={run['status']}, conclusion={run['conclusion']}, commit={run['head_commit']['message']}, url={run['html_url']}")
    else:
        print("Response text:", response.text)
except Exception as e:
    print("Error:", e)
