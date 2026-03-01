import hashlib
import time

import pandas as pd

from src.agents import get_impacted_code, get_related_faults, get_related_test_cases
from src.config import USER_STORIES
from src.explainability import summarize_results


def checksum(text):
    return hashlib.md5(text.encode()).hexdigest()


def _print_explained_block(label: str, results: list[dict]) -> None:
    print(label)
    for line in summarize_results(results):
        print(" •", line)


def watch_stories():
    last = {}
    while True:
        df = pd.read_excel(USER_STORIES)
        for _, row in df.iterrows():
            story = row["feature_sentence"]
            cs = checksum(story)
            sid = row["user_story_id"]
            if sid not in last or last[sid] != cs:
                last[sid] = cs
                print("Story changed:", sid)
                _print_explained_block("TC:", get_related_test_cases(story))
                _print_explained_block("Faults:", get_related_faults(story))
                _print_explained_block("Code:", get_impacted_code(story))
        time.sleep(10)
