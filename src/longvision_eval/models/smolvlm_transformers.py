"""Local Transformers adapter for SmolVLM2 image and multi-image models."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .base import GenerationResult, ModelAdapter, generation_options


class SmolVLMTransformersAdapter(ModelAdapter):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        try:
            import torch
            import transformers
            from transformers import AutoModelForImageTextToText, AutoProcessor
        except ImportError as error:
            raise RuntimeError(
                "SmolVLM dependencies are missing. Install the CUDA PyTorch wheel and the "
                "project's `smolvlm` optional dependencies."
            ) from error

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is required for the configured local SmolVLM test")

        self.torch = torch
        self.transformers_version = transformers.__version__
        dtype_name = config.get("compute_dtype", "bfloat16")
        compute_dtype = getattr(torch, dtype_name)
        self.processor = AutoProcessor.from_pretrained(config["model_name"])
        self.model = AutoModelForImageTextToText.from_pretrained(
            config["model_name"],
            dtype=compute_dtype,
            device_map=config.get("device_map", "auto"),
            attn_implementation="sdpa",
        )
        self.model.eval()

    def runtime_info(self) -> dict[str, Any]:
        torch = self.torch
        return {
            "adapter": self.config["adapter"],
            "torch": torch.__version__,
            "transformers": self.transformers_version,
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0),
            "model_commit": getattr(self.model.config, "_commit_hash", None),
            "quantization": "none",
        }

    @staticmethod
    def _smol_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted = []
        for message in messages:
            if message["role"] != "user":
                content = message["content"]
                if isinstance(content, str):
                    content = [{"type": "text", "text": content}]
                converted.append({"role": message["role"], "content": content})
                continue
            content = []
            for item in message["content"]:
                if item["type"] == "image":
                    content.append({"type": "image", "path": str(Path(item["path"]).resolve())})
                else:
                    content.append({"type": "text", "text": item["text"]})
            converted.append({"role": "user", "content": content})
        return converted

    def generate(self, messages: list[dict[str, Any]], generation: dict[str, Any]) -> GenerationResult:
        torch = self.torch
        inputs = self.processor.apply_chat_template(
            self._smol_messages(messages),
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)
        input_tokens = int(inputs["input_ids"].shape[-1])
        options = generation_options(generation, default_max_new_tokens=384)
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        with torch.inference_mode():
            generated = self.model.generate(**inputs, **options)
        duration = time.perf_counter() - started
        new_tokens = generated[:, input_tokens:]
        text = self.processor.batch_decode(
            new_tokens,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        peak_memory = torch.cuda.max_memory_allocated() / (1024 * 1024)
        return GenerationResult(
            text=text,
            input_tokens=input_tokens,
            output_tokens=int(new_tokens.shape[-1]),
            truncated=int(new_tokens.shape[-1]) >= options["max_new_tokens"],
            duration_seconds=round(duration, 4),
            peak_gpu_memory_mb=round(peak_memory, 2),
        )
