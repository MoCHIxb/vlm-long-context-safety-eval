"""Dependency-free adapter used to validate the experiment pipeline."""

from __future__ import annotations

from typing import Any

from .base import GenerationResult, ModelAdapter


class MockAdapter(ModelAdapter):
    def generate(self, messages: list[dict[str, Any]], generation: dict[str, Any]) -> GenerationResult:
        user_message = next(message for message in reversed(messages) if message["role"] == "user")
        text = next(item["text"] for item in user_message["content"] if item["type"] == "text")
        images = sum(1 for item in user_message["content"] if item["type"] == "image")
        response = f"MOCK_RESPONSE images={images} text={text[:80]}"
        return GenerationResult(
            text=response,
            input_tokens=sum(len(str(message).split()) for message in messages),
            output_tokens=len(response.split()),
            duration_seconds=0.0,
            peak_gpu_memory_mb=0.0,
        )
