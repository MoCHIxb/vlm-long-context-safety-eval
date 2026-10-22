"""Multi-turn experiment execution and result persistence."""

from __future__ import annotations

import json
import platform
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .dataset import load_json, load_jsonl, select_records, validate_record_assets
from .models import create_adapter


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON result without leaving a partial target file on interruption."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def user_message(turn: dict[str, Any], root: Path, response_instruction: str | None = None) -> dict[str, Any]:
    content = [
        {"type": "image", "path": str((root / image).resolve())}
        for image in turn["user"]["images"]
    ]
    text = turn["user"]["content"]
    if response_instruction:
        text = f"{text}\n\n[Response constraint: {response_instruction}]"
    content.append({"type": "text", "text": text})
    return {"role": "user", "content": content}


def run_record(
    record: dict[str, Any],
    adapter: Any,
    generation: dict[str, Any],
    root: Path,
    history_mode: str,
    system_prompt: str | None = None,
    response_instruction: str | None = None,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    outputs = []
    for index, turn in enumerate(record["turns"]):
        messages.append(user_message(turn, root, response_instruction))
        final_turn = index == len(record["turns"]) - 1
        fixed_context = history_mode == "fixed_reference" and not final_turn and turn.get("assistant_context")
        if fixed_context:
            response = {
                "text": turn["assistant_context"],
                "input_tokens": None,
                "output_tokens": None,
                "duration_seconds": 0.0,
                "peak_gpu_memory_mb": None,
                "source": "fixed_reference",
            }
        else:
            response = adapter.generate(messages, generation).to_dict()
            response["source"] = "model"
        messages.append({"role": "assistant", "content": response["text"]})
        outputs.append(
            {
                "turn_index": turn["turn_index"],
                "risk_state": turn["gold"]["risk_state"],
                "expected_behavior": turn["gold"]["expected_behavior"],
                "image_count": len(turn["user"]["images"]),
                "response": response,
            }
        )
    return {
        "sample_id": record["sample_id"],
        "pair_id": record["pair_id"],
        "track": record["track"],
        "label": record["label"],
        "condition_id": record["condition_id"],
        "risk_category": record["risk_category"],
        "turns": outputs,
    }


def load_run(config_path: Path, root: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    run_config = load_json(config_path)
    model_config = load_json(root / run_config["model_config"])
    records = load_jsonl(root / run_config["dataset_path"])
    selected = select_records(
        records,
        sample_ids=set(run_config.get("sample_ids", [])) or None,
        tracks=set(run_config.get("tracks", [])) or None,
        condition_ids=set(run_config.get("condition_ids", [])) or None,
        limit=run_config.get("limit"),
    )
    for record in selected:
        validate_record_assets(record, root)
    return run_config, model_config, selected


def execute(config_path: Path, root: Path, dry_run: bool = False, resume: bool = False) -> dict[str, Any]:
    run_config, model_config, selected = load_run(config_path, root)
    summary = {
        "run_id": run_config["run_id"],
        "model_id": model_config["model_id"],
        "sample_count": len(selected),
        "turn_count": sum(len(record["turns"]) for record in selected),
        "sample_ids": [record["sample_id"] for record in selected],
        "dry_run": dry_run,
    }
    if dry_run:
        return summary

    output_dir = root / run_config["output_dir"] / run_config["run_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    error_dir = output_dir / "errors"
    adapter = create_adapter(model_config)
    completed = 0
    skipped = 0
    failures = []
    for record in selected:
        output_path = output_dir / f"{record['sample_id']}.json"
        if resume and output_path.exists():
            skipped += 1
            continue
        try:
            result = run_record(
                record,
                adapter,
                run_config.get("generation", {}),
                root,
                run_config.get("history_mode", "interactive"),
                run_config.get("system_prompt"),
                run_config.get("response_instruction"),
            )
            result["run"] = {
                "run_id": run_config["run_id"],
                "model_id": model_config["model_id"],
                "model_name": model_config["model_name"],
                "history_mode": run_config.get("history_mode", "interactive"),
                "system_prompt": run_config.get("system_prompt"),
                "response_instruction": run_config.get("response_instruction"),
                "generation": run_config.get("generation", {}),
                "runtime": adapter.runtime_info(),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "python": sys.version,
                "platform": platform.platform(),
            }
            write_json_atomic(output_path, result)
            stale_error_path = error_dir / f"{record['sample_id']}.json"
            if stale_error_path.exists():
                stale_error_path.unlink()
            completed += 1
            print(f"[{completed + len(failures)}/{len(selected)}] wrote {output_path}", flush=True)
        except Exception as error:
            error_dir.mkdir(parents=True, exist_ok=True)
            failure = {
                "sample_id": record["sample_id"],
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            write_json_atomic(error_dir / f"{record['sample_id']}.json", failure)
            failures.append(failure)
            print(
                f"[{completed + len(failures)}/{len(selected)}] failed {record['sample_id']}: {error}",
                file=sys.stderr,
                flush=True,
            )
    summary["completed_now"] = completed
    summary["skipped_existing"] = skipped
    summary["failed_now"] = len(failures)
    summary["failed_sample_ids"] = [failure["sample_id"] for failure in failures]
    summary["output_dir"] = str(output_dir)
    write_json_atomic(output_dir / "run_summary.json", summary)
    return summary
