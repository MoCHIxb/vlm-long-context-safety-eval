"""Version guards for exploratory evaluation against unreviewed data."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_provenance(run_config: dict[str, Any], model_config: dict[str, Any], root: Path) -> dict[str, Any]:
    dataset_hash = file_sha256(root / run_config["dataset_path"])
    expected = run_config.get("expected_dataset_sha256")
    if expected and expected != dataset_hash:
        raise ValueError("Dataset differs from the configured snapshot; use a new run after data revision")
    expected_code=run_config.get('expected_code_sha256',{})
    for path,expected_hash in expected_code.items():
        if file_sha256(root/path)!=expected_hash:
            raise ValueError('Evaluation implementation differs from the configured snapshot: '+path)
    experiment_stage = run_config.get("experiment_stage", "unspecified")
    review_status = run_config.get("human_review_status", "unspecified")
    if experiment_stage == "exploratory_unreviewed" and review_status != "incomplete":
        raise ValueError("Unreviewed exploratory runs must explicitly record incomplete human review")
    canonical = json.dumps({"run": run_config, "model": model_config}, sort_keys=True, ensure_ascii=False)
    result = {
        "dataset_path": run_config["dataset_path"], "dataset_sha256": dataset_hash,
        "experiment_stage": experiment_stage, "human_review_status": review_status,
        "configuration_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }
    if expected_code:
        result['implementation_sha256']=expected_code
    return result


def require_matching_manifest(existing: dict[str, Any], current: dict[str, Any]) -> None:
    if existing.get("provenance") != current.get("provenance") or existing.get("sample_ids") != current.get("sample_ids"):
        raise ValueError("Resume manifest differs from current data/configuration or selected samples; do not mix versions")
