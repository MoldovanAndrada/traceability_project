"""Offline silver-benchmark evaluation helpers."""

from .benchmark import BenchmarkEvent, build_benchmark_events
from .metrics import compute_metrics

__all__ = ["BenchmarkEvent", "build_benchmark_events", "compute_metrics"]
