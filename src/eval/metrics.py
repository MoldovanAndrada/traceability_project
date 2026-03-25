from __future__ import annotations

from dataclasses import dataclass

K_VALUES = (1, 3, 5, 10)
TARGET_TYPES = ("code", "test_case", "fault")


def normalize_id(value: str, target_type: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""

    lowered = value.replace("\\", "/").strip().lower()
    if target_type in {"test_case", "fault"}:
        prefix = "TC" if target_type == "test_case" else "BUG"
        # Keep only numeric component for robust matching across zero-padding and case.
        digits = "".join(ch for ch in lowered if ch.isdigit())
        if digits:
            return f"{prefix}-{int(digits)}"
        return f"{prefix}-{lowered.upper()}"

    # code: support class names and file paths, with/without extension
    if "/" in lowered:
        lowered = lowered.split("/")[-1]
    if "." in lowered:
        lowered = lowered.rsplit(".", 1)[0]
    return lowered


@dataclass
class MetricAccumulator:
    eligible_events: int = 0
    total_gold_items: int = 0
    hits_at_k: dict[int, int] | None = None
    found_items_at_k: dict[int, int] | None = None
    recall_sum_at_k: dict[int, float] | None = None
    reciprocal_rank_sum: float = 0.0

    def __post_init__(self) -> None:
        self.hits_at_k = {k: 0 for k in K_VALUES}
        self.found_items_at_k = {k: 0 for k in K_VALUES}
        self.recall_sum_at_k = {k: 0.0 for k in K_VALUES}


def _accumulator_to_dict(acc: MetricAccumulator) -> dict:
    eligible = max(acc.eligible_events, 1)
    total_gold = max(acc.total_gold_items, 1)
    result = {
        "eligible_events": acc.eligible_events,
        "total_gold_items": acc.total_gold_items,
    }
    for k in K_VALUES:
        result[f"hit@{k}"] = acc.hits_at_k[k] / eligible if acc.eligible_events else 0.0
        result[f"recall@{k}_macro"] = acc.recall_sum_at_k[k] / eligible if acc.eligible_events else 0.0
        result[f"recall@{k}_micro"] = acc.found_items_at_k[k] / total_gold if acc.total_gold_items else 0.0
    result["mrr"] = acc.reciprocal_rank_sum / eligible if acc.eligible_events else 0.0
    return result


def _event_reciprocal_rank(predictions: list[str], gold: set[str]) -> float:
    for idx, value in enumerate(predictions, start=1):
        if value in gold:
            return 1.0 / idx
    return 0.0


def _evaluate_one_event(gold_items: list[str], prediction_items: list[str], target_type: str, acc: MetricAccumulator) -> None:
    normalized_gold = {normalize_id(item, target_type) for item in gold_items if normalize_id(item, target_type)}
    if not normalized_gold:
        return

    normalized_predictions = [normalize_id(item, target_type) for item in prediction_items if normalize_id(item, target_type)]

    acc.eligible_events += 1
    acc.total_gold_items += len(normalized_gold)
    acc.reciprocal_rank_sum += _event_reciprocal_rank(normalized_predictions, normalized_gold)

    for k in K_VALUES:
        top_k = normalized_predictions[:k]
        found = len(normalized_gold.intersection(top_k))
        acc.found_items_at_k[k] += found
        acc.recall_sum_at_k[k] += found / len(normalized_gold)
        acc.hits_at_k[k] += int(found > 0)


def compute_metrics(events: list[dict], predictions_by_event: dict[str, dict[str, list[str]]]) -> dict:
    per_dataset: dict[str, dict[str, MetricAccumulator]] = {}
    global_by_type = {t: MetricAccumulator() for t in TARGET_TYPES}

    for event in events:
        dataset_id = event["dataset_id"]
        per_dataset.setdefault(dataset_id, {t: MetricAccumulator() for t in TARGET_TYPES})
        event_predictions = predictions_by_event.get(event["event_id"], {})
        for target_type in TARGET_TYPES:
            gold_items = event["gold"].get(target_type, [])
            prediction_items = event_predictions.get(target_type, [])
            _evaluate_one_event(gold_items, prediction_items, target_type, per_dataset[dataset_id][target_type])
            _evaluate_one_event(gold_items, prediction_items, target_type, global_by_type[target_type])

    by_dataset_and_type = {
        dataset: {target: _accumulator_to_dict(acc) for target, acc in target_map.items()}
        for dataset, target_map in per_dataset.items()
    }

    by_dataset = {}
    for dataset, target_map in by_dataset_and_type.items():
        dataset_acc = MetricAccumulator()
        for target in TARGET_TYPES:
            source = per_dataset[dataset][target]
            dataset_acc.eligible_events += source.eligible_events
            dataset_acc.total_gold_items += source.total_gold_items
            dataset_acc.reciprocal_rank_sum += source.reciprocal_rank_sum
            for k in K_VALUES:
                dataset_acc.hits_at_k[k] += source.hits_at_k[k]
                dataset_acc.found_items_at_k[k] += source.found_items_at_k[k]
                dataset_acc.recall_sum_at_k[k] += source.recall_sum_at_k[k]
        by_dataset[dataset] = _accumulator_to_dict(dataset_acc)

    by_target_type = {target: _accumulator_to_dict(acc) for target, acc in global_by_type.items()}

    macro_rows = [row for dataset in by_dataset_and_type.values() for row in dataset.values() if row["eligible_events"]]
    macro = {
        key: (sum(row[key] for row in macro_rows) / len(macro_rows) if macro_rows else 0.0)
        for key in [f"hit@{k}" for k in K_VALUES]
        + [f"recall@{k}_macro" for k in K_VALUES]
        + [f"recall@{k}_micro" for k in K_VALUES]
        + ["mrr"]
    }

    micro_acc = MetricAccumulator()
    for target in TARGET_TYPES:
        source = global_by_type[target]
        micro_acc.eligible_events += source.eligible_events
        micro_acc.total_gold_items += source.total_gold_items
        micro_acc.reciprocal_rank_sum += source.reciprocal_rank_sum
        for k in K_VALUES:
            micro_acc.hits_at_k[k] += source.hits_at_k[k]
            micro_acc.found_items_at_k[k] += source.found_items_at_k[k]
            micro_acc.recall_sum_at_k[k] += source.recall_sum_at_k[k]

    return {
        "k_values": list(K_VALUES),
        "by_dataset": by_dataset,
        "by_target_type": by_target_type,
        "by_dataset_and_type": by_dataset_and_type,
        "macro_average": macro,
        "micro_average": _accumulator_to_dict(micro_acc),
    }
