#!/usr/bin/env python3
"""Check the USTC API using only model listing or a tiny benign prompt.

No dataset, review records, model weights, or GPU operations are used.
The explicit vision probe sends only three small generated color images.
Reads a credential from the invoking terminal environment, never from argv.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
from pathlib import Path
import random
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/generation/ustc_deepseek_flash2.json"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_config(config: dict) -> None:
    url = urlsplit(config["base_url"])
    if (url.scheme != "https" or url.hostname != "api.llm.ustc.edu.cn" or
            url.path.rstrip("/") != "/v1" or url.username or url.password or
            url.query or url.fragment or url.port not in (None, 443)):
        raise ValueError("Use exactly https://api.llm.ustc.edu.cn/v1; redirects are not followed")
    if not isinstance(config.get("model"), str) or not config["model"].strip():
        raise ValueError("An exact model ID is required")
    if not isinstance(config.get("api_key_env"), str) or not config["api_key_env"]:
        raise ValueError("An API key environment-variable name is required")


def request_json(config: dict, path: str, payload: dict | None = None):
    validate_config(config)
    key = os.environ.get(config["api_key_env"], "").strip()
    if not key:
        raise ValueError(f"Set {config['api_key_env']} in this terminal; do not pass a key on the command line")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        config["base_url"].rstrip("/") + path, data=data,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST" if payload is not None else "GET")
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=config.get("request_timeout_seconds", 120)) as response:
        # Model listing and the tiny probe must not need an unbounded response.
        body = response.read(2 * 1024 * 1024 + 1)
    if len(body) > 2 * 1024 * 1024:
        raise ValueError("Unexpectedly large preflight response")
    return json.loads(body)


def run(config: dict, *, smoke: bool):
    if not smoke:
        data = request_json(config, "/models")
        ids = sorted(item["id"] for item in data.get("data", [])
                     if isinstance(item, dict) and isinstance(item.get("id"), str))
        return {"action": "list_models", "requested_model": config["model"],
                "requested_model_listed": config["model"] in ids, "available_model_ids": ids,
                "note": "Model listing does not establish image-input support."}
    data = request_json(config, "/chat/completions", {
        "model": config["model"], "messages": [{"role": "user", "content": "Reply with exactly OK."}],
        "max_tokens": config.get("probe_max_tokens", 64), "stream": False})
    choices = data.get("choices", [])
    first = choices[0] if choices else {}
    text = first.get("message", {}).get("content")
    return {"action": "benign_smoke", "requested_model": config["model"],
            "returned_model": data.get("model"), "response_received": bool(text),
            "finish_reason": first.get("finish_reason"), "usage": data.get("usage"),
            "note": "Only a benign connectivity probe; no image or dataset generation was tested."}


def vision_payload(config: dict, colors: list[str]) -> dict:
    from PIL import Image
    rgb = {"red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255),
           "yellow": (255, 255, 0), "white": (255, 255, 255), "black": (0, 0, 0)}
    content = [{"type": "text", "text": (
        'Read the three images. Return JSON only: {"colors":["name1","name2","name3"]}, '
        'using basic English color names in image order. If you cannot access the images, '
        'return {"unavailable":true} instead of guessing.')}]
    for color in colors:
        buffer = io.BytesIO()
        Image.new("RGB", (96, 96), rgb[color]).save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + encoded}})
    return {"model": config["model"], "messages": [{"role": "user", "content": content}],
            "max_tokens": config.get("vision_probe_max_tokens", 256), "stream": False}


def run_vision(config: dict) -> dict:
    colors = random.SystemRandom().sample(["red", "green", "blue", "yellow", "white", "black"], 3)
    data = request_json(config, "/chat/completions", vision_payload(config, colors))
    first = next(iter(data.get("choices", [])), {})
    message = first.get("message", {})
    content = message.get("content") or ""
    parsed = {}
    if isinstance(content, str):
        text = content.strip()
        if text.startswith("```json\n") and text.endswith("```"):
            text = text[len("```json\n"):-3].strip()
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            pass
    observed = parsed.get("colors") if isinstance(parsed, dict) else None
    if isinstance(observed, list) and all(isinstance(c, str) for c in observed):
        observed = [c.lower().strip() for c in observed]
    matched = observed == colors and first.get("finish_reason") == "stop" and not message.get("refusal")
    return {"action": "synthetic_vision_smoke", "requested_model": config["model"],
            "returned_model": data.get("model"), "image_count": 3,
            "expected_colors": colors, "observed_colors": observed, "matched": matched,
            "finish_reason": first.get("finish_reason"), "usage": data.get("usage"),
            "dataset_files_read": 0, "gpu_used": False,
            "note": "Small randomized image-input check only; a pass does not validate dataset image understanding."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--dry-run", action="store_true")
    actions.add_argument("--list-models", action="store_true")
    actions.add_argument("--smoke", action="store_true")
    actions.add_argument("--vision-smoke", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    try:
        validate_config(config)
        if args.dry_run:
            result = {"action": "dry_run", "base_url": config["base_url"], "model": config["model"],
                      "api_key_present": bool(os.environ.get(config["api_key_env"])),
                      "network_requests": 0, "dataset_files_read": 0, "gpu_used": False}
        elif args.vision_smoke:
            result = run_vision(config)
        else:
            result = run(config, smoke=args.smoke)
    except urllib.error.HTTPError as error:
        # Never print request headers, server bodies, exception URLs or credentials.
        print(json.dumps({"status": "http_error", "http_status": error.code,
                          "note": "Check endpoint/model/access for 4xx; quota/rate limits for 429. No automatic retry."}))
        return 1
    except (urllib.error.URLError, TimeoutError):
        print(json.dumps({"status": "network_error", "note": "Check connectivity, campus access and proxy settings."}))
        return 1
    except ValueError as error:
        # Locally authored validation messages only; don't expose arbitrary response contents.
        print(json.dumps({"status": "configuration_or_response_error", "error_type": type(error).__name__,
                          "note": "Check configuration and set USTC_LLM_API_KEY in the invoking terminal."}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.list_models and not result["requested_model_listed"]:
        return 2
    if args.smoke and not result["response_received"]:
        return 2
    if args.vision_smoke and not result["matched"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
