import hashlib
import time

import pandas as pd

from src.agents import (
    get_impacted_code,
    get_related_faults,
    get_related_test_cases,
    search_with_explanations,
)
from src.config import USER_STORIES


def checksum(text):
    return hashlib.md5(text.encode()).hexdigest()


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
                print("TC:", get_related_test_cases(story))
                print("Faults:", get_related_faults(story))
                print("Code:", get_impacted_code(story))

                # Print concise factorized evidence so users can inspect why each result appeared.
                trace = search_with_explanations(story, k=5)
                print("Factorized evidence:")
                for item in trace["factorized_explanations"]:
                    print(" -", item["id"], item["evidence"])
        time.sleep(10)
