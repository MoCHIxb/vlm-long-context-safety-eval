"""Dataset loading and validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def select_records(
    records: Iterable[dict[str, Any]],
    sample_ids: set[str] | None = None,
    tracks: set[str] | None = None,
    condition_ids: set[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    selected = []
    for record in records:
        if sample_ids and record["sample_id"] not in sample_ids:
            continue
        if tracks and record["track"] not in tracks:
            continue
        if condition_ids and record["condition_id"] not in condition_ids:
            continue
        selected.append(record)
        if limit is not None and len(selected) >= limit:
            break
    if sample_ids:
        found = {record["sample_id"] for record in selected}
        missing = sample_ids - found
        if missing:
            raise ValueError(f"Sample ids not found: {sorted(missing)}")
    return selected


def validate_record_assets(record: dict[str, Any], root: Path) -> None:
    for turn in record["turns"]:
        for image in turn["user"]["images"]:
            path = (root / image).resolve()
            if not path.is_file():
                raise FileNotFoundError(f"{record['sample_id']}: missing image {path}")
