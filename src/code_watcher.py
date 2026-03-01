import time

import requests

from src.agents import search_with_explanations
from src.config import GITHUB_REPO, GITHUB_TOKEN

API = "https://api.github.com"


def get_latest_commit():
    # Get the latest commit summary
    url = f"{API}/repos/{GITHUB_REPO}/commits"
    r = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    r.raise_for_status()
    latest_commit_summary = r.json()[0]  # newest commit

    # Fetch full commit details (contains "files")
    sha = latest_commit_summary["sha"]
    commit_url = f"{API}/repos/{GITHUB_REPO}/commits/{sha}"
    r2 = requests.get(commit_url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    r2.raise_for_status()
    return r2.json()


def watch_code(interval=20):
    last_sha = None

    while True:
        commit = get_latest_commit()
        sha = commit["sha"]

        if last_sha is None:
            last_sha = sha

        elif sha != last_sha:
            print("\n🔵 GitHub: New commit detected:", sha)

            files = commit["files"]
            for f in files:
                filename = f["filename"]
                print("\n📄 Modified:", filename)

                raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{filename}"
                text = requests.get(raw_url).text

                # Run multi-index impact analysis and show factorized reasons.
                trace = search_with_explanations(text, k=12)
                results = trace["results"]

                test_cases = [r for r in results if r["type"] == "test_case"]
                faults = [r for r in results if r["type"] == "fault"]

                print("\nImpact on Test Cases:")
                for tc in test_cases:
                    print(" •", tc["id"])

                print("\nRelated Faults:")
                for bug in faults:
                    print(" •", bug["id"])

                print("\nFactorized evidence (top-3):")
                for item in trace["factorized_explanations"][:3]:
                    print(" •", item["id"], item["evidence"])

            last_sha = sha

        time.sleep(interval)
