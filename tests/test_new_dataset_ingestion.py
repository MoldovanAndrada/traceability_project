from evaluation.ground_truth_evaluation import GROUND_TRUTH_FILES, STORY_FILES, _load_code_inventory
from src.ingest import DATASET_CONFIG, SMALL_BENCHMARK_DATASETS, _ingest_dataset, validate_records


NEW_DATASETS = ("dataset restbench", "dataset safa", "dataset libEST")


def test_new_datasets_are_fully_configured():
    for dataset in NEW_DATASETS:
        assert dataset in SMALL_BENCHMARK_DATASETS
        assert dataset in DATASET_CONFIG
        assert dataset in GROUND_TRUTH_FILES
        assert dataset in STORY_FILES


def test_new_datasets_ingest_all_artifact_types():
    records = []
    for dataset in NEW_DATASETS:
        dataset_records = _ingest_dataset(dataset, DATASET_CONFIG[dataset])
        assert {record["type"] for record in dataset_records} == {
            "story",
            "test_case",
            "fault",
            "code",
        }
        records.extend(dataset_records)

    validate_records(records)


def test_ground_truth_code_paths_resolve_for_new_datasets():
    records = [
        record
        for dataset in NEW_DATASETS
        for record in _ingest_dataset(dataset, DATASET_CONFIG[dataset])
    ]
    inventory = _load_code_inventory(records)

    assert "backend/app/api/routes/items.py" in inventory["dataset restbench"]
    assert (
        "edu.nd.dronology.core/src/edu/nd/dronology/core/vehicle/internal/physicaldrone.java"
        in inventory["dataset safa"]
    )
    assert "est_client.c" in inventory["dataset libEST"]
