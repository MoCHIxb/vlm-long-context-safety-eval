"""Prepare a version-pinned exploratory gate while preserving human review files."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from longvision_eval.dataset import load_jsonl
from longvision_eval.provenance import file_sha256


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    dataset = ROOT / "data/processed/formal_v3.jsonl"
    rows = load_jsonl(dataset)
    ids = {row["sample_id"] for row in rows}
    schedules = ("static_initial_bundle", "dynamic_incremental")
    selected = []
    # Calibration seeds only; the gate checks resources, not category-level safety.
    for condition in ("C03", "C00", "C04"):
        selected.extend(f"V3H-DE-01-{condition}-{schedule}-{label}"
                        for schedule in schedules for label in ("safe", "unsafe"))
    for condition in ("B02", "B08", "B16"):
        matches = [row["sample_id"] for row in rows
                   if row["seed_id"] == "V3B-001" and row["condition_id"] == condition]
        assert len(matches) == 2
        selected.extend(matches)
    assert len(selected) == len(set(selected)) == 18
    assert set(selected) <= ids
    base = {
        "run_id": "exploratory-v3-qwen25vl7b-gate-20261030",
        "experiment_stage": "exploratory_unreviewed",
        "human_review_status": "incomplete",
        "model_config": "configs/models/qwen25vl_7b_exploratory_nf4.json",
        "dataset_path": "data/processed/formal_v3.jsonl",
        "expected_dataset_sha256": file_sha256(dataset),
        "output_dir": "outputs/exploratory_formal_v3",
        "history_mode": "fixed_reference",
        "sample_ids": selected,
        "generation": {"max_new_tokens": 512, "do_sample": False, "repetition_penalty": 1.05},
    }
    mock = copy.deepcopy(base)
    mock.update(run_id="exploratory-v3-mock-gate-20261030", model_config="configs/models/mock.json")
    destination = ROOT / "configs/runs/exploratory"
    destination.mkdir(parents=True, exist_ok=True)
    for name, payload in (("formal_v3_qwen25vl7b_gate.json", base), ("formal_v3_mock_gate.json", mock)):
        path = destination / name
        if path.exists():
            if json.loads(path.read_text(encoding="utf-8")) != payload:
                raise FileExistsError(f"Existing config differs; use a new version instead of replacing {path.name}")
        else:
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"gate_samples": len(selected), "snapshot": base["expected_dataset_sha256"],
                      "experiment_stage": base["experiment_stage"], "human_review_status": "incomplete"}, indent=2))


if __name__ == "__main__":
    main()
