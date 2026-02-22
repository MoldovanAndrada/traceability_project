import time

import requests

from src.agents import search
from src.config import GITHUB_REPO, GITHUB_TOKEN

API = "https://api.github.com"


def _headers() -> dict:
    return {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def get_latest_commit():
    # Get the latest commit summary
    url = f"{API}/repos/{GITHUB_REPO}/commits"
    r = requests.get(url, headers=_headers(), timeout=30)
    r.raise_for_status()
    commits = r.json()
    if not commits:
        raise RuntimeError("GitHub API returned no commits for repository")
    latest_commit_summary = commits[0]  # newest commit

    # Fetch full commit details (contains "files")
    sha = latest_commit_summary["sha"]
    commit_url = f"{API}/repos/{GITHUB_REPO}/commits/{sha}"
    r2 = requests.get(commit_url, headers=_headers(), timeout=30)
    r2.raise_for_status()
    return r2.json()


def watch_code(interval=20, dataset: str | None = None):
    last_sha = None

    while True:
        try:
            commit = get_latest_commit()
        except requests.RequestException as exc:
            print("\n⚠️ GitHub request failed:", exc)
            time.sleep(interval)
            continue
        except RuntimeError as exc:
            print("\n⚠️ GitHub watcher warning:", exc)
            time.sleep(interval)
            continue

        sha = commit["sha"]

        if last_sha is None:
            print("\n🟢 GitHub: Tracking latest commit:", sha)
            last_sha = sha

        elif sha != last_sha:
            print("\n🔵 GitHub: New commit detected:", sha)

            files = commit.get("files", [])
            for f in files:
                filename = f["filename"]
                print("\n📄 Modified:", filename)

                raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{filename}"
                text = requests.get(raw_url, timeout=30).text

                # Run semantic impact analysis
                results = search(text, dataset=dataset)

                test_cases = [r for r in results if r["type"] == "test_case"]
                faults = [r for r in results if r["type"] == "fault"]

                print("\nImpact on Test Cases:")
                for tc in test_cases:
                    print(" •", tc["id"])

                print("\nRelated Faults:")
                for bug in faults:
                    print(" •", bug["id"])

            last_sha = sha

        time.sleep(interval)
