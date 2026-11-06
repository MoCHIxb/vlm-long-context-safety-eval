#!/usr/bin/env python3
"""Stage pinned model weights and verify interfaces without starting dataset runs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(ROOT / ".cache" / "huggingface"))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "120")

PATTERNS = ["*.json", "*.jinja", "*.txt", "*.model", "*.safetensors", "README.md", "LICENSE*"]


def inspect_snapshot(snapshot: Path) -> dict:
    """Require all indexed shards; directory existence alone is not readiness."""
    missing = []
    required = {"config.json", "tokenizer_config.json", "preprocessor_config.json"}
    if not (snapshot / "tokenizer.json").is_file() and not (snapshot / "tokenizer.model").is_file():
        missing.append("tokenizer.json or tokenizer.model")
    index = snapshot / "model.safetensors.index.json"
    if index.is_file():
        required.update(json.loads(index.read_text(encoding="utf-8"))["weight_map"].values())
    else:
        required.add("model.safetensors")
    missing.extend(sorted(name for name in required if not (snapshot / name).is_file()))
    weights = sorted(name for name in required if name.endswith(".safetensors") and (snapshot / name).is_file())
    if not weights:
        missing.append("nonempty safetensors weight set")
    # Read safetensors headers, never materialize tensors in RAM or GPU.
    if not missing:
        from safetensors import safe_open
        for name in weights:
            with safe_open(snapshot / name, framework="pt", device="cpu") as handle:
                if not list(handle.keys()):
                    raise ValueError(f"Empty weight shard: {name}")
    return {"weights_complete": not missing, "missing_files": missing,
            "weight_files": len(weights), "weight_bytes": sum((snapshot / n).stat().st_size for n in weights)}


def processor_check(config: dict) -> dict:
    """Synthetic, benign multi-image history; no model weights or dataset read."""
    from PIL import Image
    from transformers import AutoProcessor
    from longvision_eval.models.qwen_transformers import QwenTransformersAdapter
    options = {k: config[k] for k in ("revision", "local_files_only", "min_pixels", "max_pixels") if k in config}
    processor = AutoProcessor.from_pretrained(config["model_name"], **options)
    with tempfile.TemporaryDirectory(prefix="model-processor-", dir=ROOT / "outputs" / "model_deployment") as folder:
        images = []
        for color in ("red", "blue"):
            path = Path(folder) / f"{color}.png"
            Image.new("RGB", (128, 128), color=color).save(path)
            images.append({"type": "image", "path": str(path)})
        schedules = {
            "static": [{"role": "user", "content": [*images, {"type": "text", "text": "Look at these images."}]},
                       {"role": "assistant", "content": "I see two images."},
                       {"role": "user", "content": [{"type": "text", "text": "Name their colors in order."}]}],
            "dynamic": [{"role": "user", "content": [images[0], {"type": "text", "text": "Look at this image."}]},
                        {"role": "assistant", "content": "I see the first image."},
                        {"role": "user", "content": [images[1], {"type": "text", "text": "Name both colors in order."}]}],
        }
        counts = {}
        for name, messages in schedules.items():
            converted = QwenTransformersAdapter._qwen_messages(messages)
            rendered = processor.apply_chat_template(converted, tokenize=False, add_generation_prompt=True)
            for message in converted:
                for item in message["content"]:
                    if item["type"] == "text" and item["text"] not in rendered:
                        raise ValueError("Chat template silently dropped a reference/user text turn")
            inputs = processor.apply_chat_template(
                converted, tokenize=True,
                add_generation_prompt=True, return_dict=True, return_tensors="pt",
                processor_kwargs=config.get("processor_call_options", {}))
            if "pixel_values" not in inputs:
                raise ValueError("Processor dropped image inputs")
            counts[name] = {"input_tokens": int(inputs["input_ids"].shape[-1]),
                            "all_text_turns_preserved": True,
                            "pixel_values_shape": list(inputs["pixel_values"].shape)}
        return {"passed": True, "processor_class": type(processor).__name__, "synthetic_inputs": counts}


def gpu_free_mib() -> int:
    completed = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                               check=True, capture_output=True, text=True)
    return int(completed.stdout.strip().splitlines()[0])


def smoke_check(config: dict) -> dict:
    """Load one model and test two-image generation, releasing it on completion."""
    import gc
    import torch
    from PIL import Image
    from longvision_eval.models import create_adapter
    free = gpu_free_mib()
    if free < config["minimum_free_gpu_mib"]:
        return {"passed": False, "status": "waiting_for_gpu", "free_gpu_mib": free,
                "required_free_gpu_mib": config["minimum_free_gpu_mib"]}
    adapter = None
    try:
        adapter = create_adapter(config)
        results = []
        with tempfile.TemporaryDirectory(prefix="model-smoke-", dir=ROOT / "outputs" / "model_deployment") as folder:
            paths = []
            for color in ("red", "blue"):
                path = Path(folder) / f"{color}.png"
                Image.new("RGB", (128, 128), color=color).save(path)
                paths.append({"type": "image", "path": str(path)})
            for dynamic in (False, True):
                messages = [{"role": "user", "content": [paths[0], *([] if dynamic else [paths[1]]),
                             {"type": "text", "text": "Look at the image or images."}]},
                            {"role": "assistant", "content": "I will examine the images."},
                            {"role": "user", "content": [*([paths[1]] if dynamic else []),
                             {"type": "text", "text": "Name the two solid colors in order. Answer briefly."}]}]
                response = adapter.generate(messages, {"max_new_tokens": 64, "do_sample": False})
                value = response.to_dict()
                value["schedule"] = "dynamic" if dynamic else "static"
                value["expected_colors_present"] = all(c in response.text.lower() for c in ("red", "blue"))
                results.append(value)
        passed = all(r["text"].strip() and not r["truncated"] and r["expected_colors_present"] for r in results)
        return {"passed": passed, "status": "passed" if passed else "needs_manual_inspection",
                "runtime": adapter.runtime_info(), "responses": results,
                "scope": "synthetic two-image smoke only; does not validate 16K memory or safety"}
    finally:
        del adapter
        gc.collect()
        torch.cuda.empty_cache()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", help="Model key; repeat or omit for all")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--include-gated", action="store_true", help="User has obtained Gemma access and logged in locally")
    parser.add_argument("--processor-check", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="GPU loading allowed; never starts dataset experiments")
    args = parser.parse_args()
    plan = json.loads((ROOT / "configs/deployment/open_models.json").read_text(encoding="utf-8"))
    models = plan["models"]
    if args.model:
        unknown = set(args.model) - {m["key"] for m in models}
        if unknown:
            parser.error(f"Unknown model keys: {sorted(unknown)}")
        models = [m for m in models if m["key"] in args.model]
    output_dir = ROOT / "outputs/model_deployment"
    output_dir.mkdir(parents=True, exist_ok=True)
    lock = output_dir / "deployment.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit("Another deployment may be active; inspect deployment.lock before retrying")
    os.close(descriptor)
    try:
        from huggingface_hub import HfApi, snapshot_download
        from huggingface_hub.errors import GatedRepoError
        from longvision_eval.runner import write_json_atomic
        config_dir = ROOT / "configs/models/deployment"
        config_dir.mkdir(parents=True, exist_ok=True)
        for config in models:
            report_path = output_dir / f"{config['key']}.json"
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
            report.update(model_key=config["key"], model_name=config["model_name"], revision=config["revision"],
                          updated_at_utc=datetime.now(timezone.utc).isoformat(),
                          dataset_runs_started=False,
                          dependencies={p: importlib.metadata.version(p) for p in
                                        ("torch", "transformers", "accelerate", "bitsandbytes", "huggingface-hub", "pillow")})
            write_json_atomic(config_dir / f"{config['key']}_nf4.json", config)
            snapshot = Path(os.environ["HF_HOME"]) / "hub" / ("models--" + config["model_name"].replace("/", "--")) / "snapshots" / config["revision"]
            report["snapshot"] = str(snapshot)
            step = "inventory"
            try:
                report["inventory"] = inspect_snapshot(snapshot)
                if (config["key"] == "gemma3_12b" and not report["inventory"]["weights_complete"]
                        and not args.include_gated):
                    report["status"] = "waiting_for_user_license_and_hf_login"
                    write_json_atomic(report_path, report)
                    print(json.dumps({"key": config["key"], "status": report["status"]}), flush=True)
                    continue
                if args.download and not report["inventory"]["weights_complete"]:
                    step = "download"
                    info = HfApi().model_info(config["model_name"], revision=config["revision"], files_metadata=True)
                    # Check permission before reserving large disk space or trying weight downloads.
                    from huggingface_hub import hf_hub_download
                    hf_hub_download(config["model_name"], "config.json", revision=config["revision"])
                    from fnmatch import fnmatch
                    required = [f for f in info.siblings if any(fnmatch(f.rfilename, p) for p in PATTERNS)]
                    missing_bytes = sum(f.size or 0 for f in required if not (snapshot / f.rfilename).is_file())
                    free = shutil.disk_usage(ROOT).free
                    reserve = plan["minimum_disk_free_gib_after_download"] * 1024**3
                    if free - missing_bytes < reserve:
                        report["download"] = {"status": "waiting_for_disk", "missing_bytes": missing_bytes,
                                              "free_bytes": free, "reserve_bytes": reserve}
                    else:
                        report["status"] = "downloading"
                        report["download"] = {"status": "downloading", "missing_bytes": missing_bytes}
                        write_json_atomic(report_path, report)
                        print(f"Downloading {config['model_name']} @ {config['revision']}", flush=True)
                        snapshot_download(config["model_name"], revision=config["revision"], allow_patterns=PATTERNS, max_workers=2)
                        report["download"] = {"status": "complete"}
                        report["inventory"] = inspect_snapshot(snapshot)
                if report["inventory"]["weights_complete"]:
                    if args.processor_check:
                        step = "processor_check"
                        report["processor_check"] = processor_check(config)
                    if args.smoke:
                        step = "smoke_check"
                        report["smoke_check"] = smoke_check(config)
                    report["status"] = "weights_ready"
                    if report.get("processor_check", {}).get("passed"):
                        report["status"] = "processor_ready_gpu_unverified"
                    if report.get("smoke_check", {}).get("passed"):
                        report["status"] = "synthetic_smoke_passed"
                else:
                    report["status"] = report.get("download", {}).get("status", "weights_missing")
                report.pop("error_type", None)
            except GatedRepoError:
                report["status"] = "waiting_for_user_license_and_hf_login"
            except Exception as error:
                # Do not serialize exception URLs/headers, which may contain credentials.
                report["status"] = "error"
                report["error_type"] = type(error).__name__
                report["failed_step"] = step
                if step in {"processor_check", "smoke_check"}:
                    report["error_detail"] = str(error)[:500]
                print(f"{config['key']}: {type(error).__name__}", flush=True)
            report["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            write_json_atomic(report_path, report)
            print(json.dumps({"key": config["key"], "status": report["status"],
                              "report": str(report_path)}, ensure_ascii=False), flush=True)
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
