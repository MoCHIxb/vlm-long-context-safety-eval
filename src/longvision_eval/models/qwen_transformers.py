"""Local Transformers adapter for Qwen2.5-VL and compatible Qwen VLMs."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .base import GenerationResult, ModelAdapter, generation_options


class QwenTransformersAdapter(ModelAdapter):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        try:
            import torch
            from transformers import AutoProcessor, BitsAndBytesConfig, Qwen2_5_VLForConditionalGeneration
        except ImportError as error:
            raise RuntimeError(
                "Qwen dependencies are missing. Install the CUDA PyTorch wheel and then run "
                "`python -m pip install -e .[qwen]`."
            ) from error

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is required for the configured local Qwen smoke test")

        self.torch = torch
        dtype_name = config.get("compute_dtype", "bfloat16")
        compute_dtype = getattr(torch, dtype_name)
        quantization = None
        if config.get("load_in_4bit", False):
            quantization = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=compute_dtype,
            )

        processor_options = {}
        for key in ("min_pixels", "max_pixels"):
            if key in config:
                processor_options[key] = config[key]
        self.processor = AutoProcessor.from_pretrained(config["model_name"], **processor_options)
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            config["model_name"],
            dtype=compute_dtype,
            device_map=config.get("device_map", "auto"),
            quantization_config=quantization,
            attn_implementation="sdpa",
        )
        self.model.eval()

    def runtime_info(self) -> dict[str, Any]:
        import bitsandbytes
        import transformers

        torch = self.torch
        return {
            "adapter": self.config["adapter"],
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "bitsandbytes": bitsandbytes.__version__,
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0),
            "model_commit": getattr(self.model.config, "_commit_hash", None),
            "quantization": "nf4-4bit" if self.config.get("load_in_4bit") else "none",
        }

    @staticmethod
    def _qwen_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted = []
        for message in messages:
            if message["role"] != "user":
                converted.append({"role": message["role"], "content": message["content"]})
                continue
            content = []
            for item in message["content"]:
                if item["type"] == "image":
                    # Transformers 5.x on Windows can misread file:// URIs through
                    # TorchVision. An absolute local path is decoded correctly.
                    content.append({"type": "image", "image": str(Path(item["path"]).resolve())})
                else:
                    content.append({"type": "text", "text": item["text"]})
            converted.append({"role": "user", "content": content})
        return converted

    def generate(self, messages: list[dict[str, Any]], generation: dict[str, Any]) -> GenerationResult:
        torch = self.torch
        qwen_messages = self._qwen_messages(messages)
        inputs = self.processor.apply_chat_template(
            qwen_messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.model.device)
        input_tokens = int(inputs["input_ids"].shape[-1])
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        options = generation_options(generation, default_max_new_tokens=128)
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
