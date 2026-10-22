"""Model adapter registry."""

from __future__ import annotations

from typing import Any

from .base import ModelAdapter
from .mock import MockAdapter


def create_adapter(config: dict[str, Any]) -> ModelAdapter:
    adapter = config["adapter"]
    if adapter == "mock":
        return MockAdapter(config)
    if adapter == "qwen_transformers":
        from .qwen_transformers import QwenTransformersAdapter

        return QwenTransformersAdapter(config)
    if adapter == "smolvlm_transformers":
        from .smolvlm_transformers import SmolVLMTransformersAdapter

        return SmolVLMTransformersAdapter(config)
    raise ValueError(f"Unknown model adapter: {adapter}")
