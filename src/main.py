import argparse
import threading

from src.code_watcher import watch_code
from src.config import DEFAULT_PROJECT
from src.watcher import watch_stories


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Traceability watchers")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help="Dataset key to monitor (lang|time|math)")
    parser.add_argument("--stories-only", action="store_true", help="Run only the user-story watcher")
    args = parser.parse_args()

    workers = [threading.Thread(target=watch_stories, kwargs={"project_name": args.project})]

    if not args.stories_only:
        workers.append(threading.Thread(target=watch_code, kwargs={"dataset": args.project}))

    for worker in workers:
        worker.start()

    for worker in workers:
        worker.join()
