"""Internal model adapter contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


def generation_options(generation: dict[str, Any], default_max_new_tokens: int) -> dict[str, Any]:
    """Translate the shared run configuration into Transformers generation options."""
    options: dict[str, Any] = {
        "max_new_tokens": int(generation.get("max_new_tokens", default_max_new_tokens)),
        "do_sample": bool(generation.get("do_sample", False)),
    }
    if options["do_sample"]:
        options["temperature"] = float(generation.get("temperature", 0.7))
        options["top_p"] = float(generation.get("top_p", 0.9))
    if "repetition_penalty" in generation:
        options["repetition_penalty"] = float(generation["repetition_penalty"])
    if "no_repeat_ngram_size" in generation:
        options["no_repeat_ngram_size"] = int(generation["no_repeat_ngram_size"])
    return options


@dataclass
class GenerationResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    truncated: bool | None = None
    duration_seconds: float | None = None
    peak_gpu_memory_mb: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelAdapter(ABC):
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.model_id = config["model_id"]

    def runtime_info(self) -> dict[str, Any]:
        return {"adapter": self.config["adapter"]}

    @abstractmethod
    def generate(self, messages: list[dict[str, Any]], generation: dict[str, Any]) -> GenerationResult:
        """Generate one assistant response for the complete conversation history."""
