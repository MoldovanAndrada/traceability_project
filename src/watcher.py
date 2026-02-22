
import time, hashlib, pandas as pd
from src.config import USER_STORIES
from src.agents import get_related_test_cases, get_related_faults, get_impacted_code

def checksum(text):
    return hashlib.md5(text.encode()).hexdigest()

def watch_stories():
    last = {}
    while True:
        df = pd.read_excel(USER_STORIES)
        for _, row in df.iterrows():
            story = row['feature_sentence']
            cs = checksum(story)
            sid = row['user_story_id']
            if sid not in last or last[sid]!=cs:
                last[sid]=cs
                print("Story changed:", sid)
                print("TC:", get_related_test_cases(story))
                print("Faults:", get_related_faults(story))
                print("Code:", get_impacted_code(story))
        time.sleep(10)
