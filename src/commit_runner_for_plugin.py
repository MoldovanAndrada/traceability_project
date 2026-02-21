import json
from src.code_watcher import get_latest_commit
from src.agents import search

def run_once():
    commit = get_latest_commit()
    sha = commit["sha"]

    impacted = []

    for f in commit["files"]:
        filename = f["filename"]
        text = f.get("patch", "")

        results = search(text)

        impacted.append({
            "file": filename,
            "results": results
        })

    print(json.dumps({
        "sha": sha,
        "impact": impacted
    }))

if __name__ == "__main__":
    run_once()