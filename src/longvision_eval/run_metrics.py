"""Operational metrics for completed model runs."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .annotation import load_results


def summarize_runs(run_dirs: Iterable[Path]) -> dict[str, Any]:
    run_dirs=list(run_dirs)
    results = load_results(run_dirs)
    calls = [turn["response"] for result in results for turn in result["turns"]]
    final_calls = [result["turns"][-1]["response"] for result in results]
    paired: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        paired[(result["run"]["model_id"], result["pair_id"])][result["label"]] = result

    exact_prefix_pairs = 0
    comparable_pairs = 0
    for variants in paired.values():
        if {"safe", "unsafe"} <= variants.keys():
            comparable_pairs += 1
            safe_turns = variants["safe"]["turns"][:-1]
            unsafe_turns = variants["unsafe"]["turns"][:-1]
            if [turn["response"]["text"] for turn in safe_turns] == [
                turn["response"]["text"] for turn in unsafe_turns
            ]:
                exact_prefix_pairs += 1

    def maximum(field: str) -> float | int | None:
        values = [call[field] for call in calls if call.get(field) is not None]
        return max(values) if values else None

    return {
        "sample_count": len(results),
        "model_ids": sorted({result["run"]["model_id"] for result in results}),
        "call_count": len(calls),
        "model_generated_call_count": sum(call.get('source','model')=='model' for call in calls),
        "fixed_reference_call_count": sum(call.get('source')=='fixed_reference' for call in calls),
        "error_file_count": sum(len(list((path/'errors').glob('*.json'))) for path in run_dirs),
        "truncated_calls": sum(bool(call.get("truncated")) for call in calls),
        "truncated_final_calls": sum(bool(call.get("truncated")) for call in final_calls),
        "max_input_tokens": maximum("input_tokens"),
        "max_output_tokens": maximum("output_tokens"),
        "max_peak_gpu_memory_mb": maximum("peak_gpu_memory_mb"),
        "total_generation_seconds": round(
            sum(float(call.get("duration_seconds") or 0) for call in calls), 4
        ),
        "comparable_safe_unsafe_pairs": comparable_pairs,
        "exact_shared_prefix_pairs": exact_prefix_pairs,
    }
