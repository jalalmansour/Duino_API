"""
Duino API — Inference Engine
Loads Gemma 4 (and other HuggingFace models) with auto-quantization.
Supports both streaming and batch generation.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class InferRequest:
    messages: list[dict]          # [{"role": "user", "content": "..."}]
    model_id: str = "gemma-4-2b"
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.95
    stream: bool = False
    session_id: str | None = None


@dataclass
class InferResult:
    request_id: str
    text: str
    model_id: str
    tokens_in: int
    tokens_out: int
    ttft_ms: float        # time to first token
    total_ms: float
    finish_reason: str    # "stop" | "length" | "error"


# ─── Model config registry ────────────────────────────────────────────────────

@dataclass
class ModelConfig:
    model_id: str
    hf_name: str
    max_len: int = 8192
    quant: str | None = None        # overridden by GPU detection
    dtype: str = "auto"
    trust_remote: bool = False


GEMMA4_MODELS: dict[str, ModelConfig] = {
    "gemma-4-2b": ModelConfig(
        model_id="gemma-4-2b",
        hf_name="google/gemma-4-2b-it",
        max_len=8192,
    ),
    "gemma-4-9b": ModelConfig(
        model_id="gemma-4-9b",
        hf_name="google/gemma-4-9b-it",
        max_len=8192,
    ),
    "gemma-4-27b": ModelConfig(
        model_id="gemma-4-27b",
        hf_name="google/gemma-4-27b-it",
        max_len=4096,
    ),
}


# ─── Engine ───────────────────────────────────────────────────────────────────

class InferenceEngine:
    """
    Loads a HuggingFace model with optional quantization.
    Uses vLLM on Linux if available, falls back to transformers pipeline.
    """

    def __init__(self, model_cfg: ModelConfig, device: str = "cpu", quant: str | None = None):
        self.cfg = model_cfg
        self.device = device
        self.quant = quant or model_cfg.quant
        self._pipe = None
        self._tokenizer = None
        self.loaded = False

    def load(self) -> None:
        """Synchronous model loading (call once at startup)."""
        from duino_api.config import settings
        import os
        os.environ["HF_HOME"] = settings.hf_home
        if settings.hf_token:
            os.environ["HUGGING_FACE_HUB_TOKEN"] = settings.hf_token

        # Try vLLM (Linux + GPU only)
        if self.device == "cuda" and self._try_vllm():
            self.loaded = True
            return

        # Fallback: transformers
        self._load_transformers()
        self.loaded = True

    def _try_vllm(self) -> bool:
        try:
            from vllm import LLM, SamplingParams  # type: ignore
            self._vllm = LLM(
                model=self.cfg.hf_name,
                max_model_len=self.cfg.max_len,
                quantization=self.quant,
                dtype=self.cfg.dtype,
                gpu_memory_utilization=0.85,
            )
            self._backend = "vllm"
            return True
        except Exception:
            return False

    def _load_transformers(self) -> None:
        from transformers import AutoTokenizer, pipeline
        import torch

        bnb_cfg = None
        if self.quant == "bnb-4bit":
            from transformers import BitsAndBytesConfig
            bnb_cfg = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
        elif self.quant == "bnb-8bit":
            from transformers import BitsAndBytesConfig
            bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)

        self._tokenizer = AutoTokenizer.from_pretrained(self.cfg.hf_name)
        self._pipe = pipeline(
            "text-generation",
            model=self.cfg.hf_name,
            tokenizer=self._tokenizer,
            device_map="auto" if self.device == "cuda" else "cpu",
            quantization_config=bnb_cfg,
            torch_dtype="auto",
        )
        self._backend = "transformers"

    # ── Inference ────────────────────────────────────────────────────────────

    def _build_prompt(self, messages: list[dict]) -> str:
        """Convert chat messages to Gemma chat template."""
        if self._tokenizer and hasattr(self._tokenizer, "apply_chat_template"):
            return self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        # Fallback: simple concatenation
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            parts.append(f"<{role}>{content}</{role}>")
        parts.append("<assistant>")
        return "\n".join(parts)

    async def generate(self, req: InferRequest) -> InferResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_generate, req)

    def _sync_generate(self, req: InferRequest) -> InferResult:
        prompt = self._build_prompt(req.messages)
        t0 = time.perf_counter()
        request_id = str(uuid.uuid4())

        if self._backend == "vllm":
            from vllm import SamplingParams  # type: ignore
            params = SamplingParams(
                max_tokens=req.max_tokens,
                temperature=req.temperature,
                top_p=req.top_p,
            )
            outputs = self._vllm.generate([prompt], params)
            text = outputs[0].outputs[0].text
            tokens_out = len(outputs[0].outputs[0].token_ids)
        else:
            out = self._pipe(
                prompt,
                max_new_tokens=req.max_tokens,
                temperature=req.temperature,
                top_p=req.top_p,
                do_sample=req.temperature > 0,
                return_full_text=False,
            )
            text = out[0]["generated_text"]
            tokens_out = len(text.split())

        total = (time.perf_counter() - t0) * 1000
        tokens_in = len(prompt.split())

        return InferResult(
            request_id=request_id,
            text=text,
            model_id=req.model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            ttft_ms=total * 0.1,  # approximation without streaming
            total_ms=total,
            finish_reason="stop",
        )

    async def stream(self, req: InferRequest) -> AsyncIterator[str]:
        """Yield tokens one-by-one (transformers TextIteratorStreamer)."""
        if self._backend == "vllm":
            # vLLM streaming not wrapped here — yield full text in one chunk
            result = await self.generate(req)
            yield result.text
            return

        from transformers import TextIteratorStreamer
        import threading

        prompt = self._build_prompt(req.messages)
        streamer = TextIteratorStreamer(
            self._tokenizer, skip_special_tokens=True, skip_prompt=True
        )
        inputs = self._tokenizer(prompt, return_tensors="pt")

        def _run():
            self._pipe.model.generate(
                **inputs,
                max_new_tokens=req.max_tokens,
                temperature=req.temperature,
                top_p=req.top_p,
                do_sample=req.temperature > 0,
                streamer=streamer,
            )

        thread = threading.Thread(target=_run)
        thread.start()

        for chunk in streamer:
            yield chunk
            await asyncio.sleep(0)

        thread.join()

    def unload(self) -> None:
        """Release GPU memory."""
        try:
            import torch
            if hasattr(self, "_pipe") and self._pipe:
                del self._pipe
            if hasattr(self, "_vllm") and self._vllm:
                del self._vllm
            torch.cuda.empty_cache()
        except Exception:
            pass
        self.loaded = False
