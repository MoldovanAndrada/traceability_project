from src.eval.metrics import compute_metrics


def test_compute_metrics_excludes_empty_gold_denominator() -> None:
    events = [
        {
            "event_id": "e1",
            "dataset_id": "d1",
            "gold": {"code": ["A"], "test_case": [], "fault": ["Bug-01"]},
        },
        {
            "event_id": "e2",
            "dataset_id": "d1",
            "gold": {"code": [], "test_case": ["TC-001"], "fault": []},
        },
    ]

    predictions = {
        "e1": {"code": ["a", "B"], "test_case": ["TC-001"], "fault": ["Bug-09", "Bug-01"]},
        "e2": {"code": ["A"], "test_case": ["TC-001"], "fault": ["Bug-02"]},
    }

    metrics = compute_metrics(events, predictions)

    code_metrics = metrics["by_target_type"]["code"]
    assert code_metrics["eligible_events"] == 1
    assert code_metrics["hit@1"] == 1.0

    test_metrics = metrics["by_target_type"]["test_case"]
    assert test_metrics["eligible_events"] == 1
    assert test_metrics["recall@1_micro"] == 1.0

    fault_metrics = metrics["by_target_type"]["fault"]
    assert fault_metrics["eligible_events"] == 1
    assert fault_metrics["hit@1"] == 0.0
    assert fault_metrics["hit@3"] == 1.0
