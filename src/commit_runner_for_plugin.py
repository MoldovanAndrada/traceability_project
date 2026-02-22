import json
from src.agentic_traceability import AgenticTraceabilityEngine
from src.code_watcher import get_latest_commit

ENGINE = AgenticTraceabilityEngine()


def run_once():
    commit = get_latest_commit()
    report = ENGINE.analyze_commit(commit)
    print(json.dumps(report))


if __name__ == "__main__":
    run_once()
