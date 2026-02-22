import hashlib
import time

import pandas as pd

from src.agents import get_impacted_code, get_related_faults, get_related_test_cases
from src.config import DEFAULT_PROJECT, resolve_project


def checksum(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _read_table(path: str) -> pd.DataFrame:
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


def watch_stories(project_name: str = DEFAULT_PROJECT, interval: int = 10):
    project = resolve_project(project_name)
    last = {}

    while True:
        df = _read_table(project["stories_path"])
        for _, row in df.iterrows():
            story = row["feature_sentence"]
            story_id = row["user_story_id"]
            cs = checksum(story)

            if story_id not in last or last[story_id] != cs:
                last[story_id] = cs
                print(f"[{project_name}] Story changed: {story_id}")
                print("TC:", get_related_test_cases(story, dataset=project_name))
                print("Faults:", get_related_faults(story, dataset=project_name))
                print("Code:", get_impacted_code(story, dataset=project_name))

        time.sleep(interval)
