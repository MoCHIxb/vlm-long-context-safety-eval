"""Internal model adapter contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


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
