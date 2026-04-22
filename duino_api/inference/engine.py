"""
Duino API — Inference Engine (Multi-GPU Edition)
Loads Gemma 4 across ALL available GPUs automatically.
- vLLM: tensor_parallel_size = gpu_count (full parallelism)
- transformers: device_map="auto" (automatic layer sharding across GPUs)
- bitsandbytes: 4-bit / 8-bit with multi-GPU shard
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class InferRequest:
    messages: list[dict]
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
    ttft_ms: float
    total_ms: float
    finish_reason: str


@dataclass
class ModelConfig:
    model_id: str
    hf_name: str
    max_len: int = 8192
    quant: str | None = None
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


# ─── GPU inventory ────────────────────────────────────────────────────────────

def _count_gpus() -> int:
    """Return number of CUDA GPUs available."""
    try:
        import torch
        return torch.cuda.device_count()
    except Exception:
        return 0


def _gpu_info() -> list[dict]:
    """Return list of GPU info dicts: {name, vram_mb, index}."""
    import subprocess, re
    try:
        out = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=index,name,memory.total,memory.free,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        gpus = []
        for line in out.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5:
                gpus.append({
                    "index":   int(parts[0]),
                    "name":    parts[1],
                    "vram_mb": int(parts[2]),
                    "free_mb": int(parts[3]),
                    "util_pct": int(parts[4]),
                })
        return gpus
    except Exception:
        return []


# ─── Engine ───────────────────────────────────────────────────────────────────

class InferenceEngine:
    """
    Multi-GPU inference engine.

    Strategy:
    1. vLLM (Linux + CUDA): tensor_parallel_size = all GPUs → true tensor parallelism
    2. transformers + device_map="auto": HF Accelerate shards layers across GPUs
    3. CPU fallback if no GPU
    """

    def __init__(self, model_cfg: ModelConfig, quant: str | None = None):
        self.cfg   = model_cfg
        self.quant = quant or model_cfg.quant
        self._pipe = None
        self._tokenizer = None
        self._backend: str = "unloaded"
        self.loaded = False
        self.gpu_count = _count_gpus()
        self.device = "cuda" if self.gpu_count > 0 else "cpu"

    def load(self) -> None:
        """Load model across all available GPUs."""
        from duino_api.config import settings

        os.environ["HF_HOME"] = settings.hf_home
        if settings.hf_token:
            os.environ["HUGGING_FACE_HUB_TOKEN"] = settings.hf_token
            os.environ["HF_TOKEN"] = settings.hf_token

        print(f"[Engine] GPUs: {self.gpu_count} | device: {self.device} | quant: {self.quant}")

        if self.device == "cuda":
            # Try vLLM with all GPUs (tensor parallelism)
            if self._try_vllm():
                self.loaded = True
                return
            # Fallback: transformers multi-GPU
            self._load_transformers()
        else:
            self._load_transformers()

        self.loaded = True

    # ── vLLM (full tensor parallelism across all GPUs) ────────────────────────

    def _try_vllm(self) -> bool:
        try:
            from vllm import LLM  # type: ignore
            tensor_parallel = max(1, self.gpu_count)
            print(f"[Engine] Loading via vLLM (tensor_parallel={tensor_parallel})")
            self._vllm = LLM(
                model=self.cfg.hf_name,
                max_model_len=self.cfg.max_len,
                quantization=self.quant if self.quant not in ("bnb-4bit", "bnb-8bit") else None,
                dtype=self.cfg.dtype,
                gpu_memory_utilization=0.92,  # use 92% of each GPU's VRAM
                tensor_parallel_size=tensor_parallel,
            )
            self._backend = "vllm"
            print(f"[Engine] ✅ vLLM loaded on {tensor_parallel} GPU(s)")
            return True
        except Exception as exc:
            print(f"[Engine] vLLM unavailable ({exc}) — falling back to transformers")
            return False

    # ── transformers (device_map=auto shards across all GPUs) ─────────────────

    def _load_transformers(self) -> None:
        import torch
        from transformers import AutoTokenizer, pipeline

        print(f"[Engine] Loading via transformers (device_map=auto, gpus={self.gpu_count})")

        bnb_cfg = None
        if self.quant == "bnb-4bit" and self.device == "cuda":
            from transformers import BitsAndBytesConfig
            bnb_cfg = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
            print("[Engine] Using BNB 4-bit quantization")
        elif self.quant == "bnb-8bit" and self.device == "cuda":
            from transformers import BitsAndBytesConfig
            bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
            print("[Engine] Using BNB 8-bit quantization")

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.cfg.hf_name,
            trust_remote_code=self.cfg.trust_remote,
        )

        # device_map="auto" automatically shards layers across ALL visible GPUs
        # On Kaggle with 2×T4 or 2×P100 this fills both GPUs
        self._pipe = pipeline(
            "text-generation",
            model=self.cfg.hf_name,
            tokenizer=self._tokenizer,
            device_map="auto",                    # ← key: uses ALL GPUs
            quantization_config=bnb_cfg,
            torch_dtype="auto",
            model_kwargs={
                "max_memory": _build_max_memory(self.gpu_count),
            },
        )
        self._backend = "transformers"
        print(f"[Engine] ✅ transformers loaded | backend=transformers | GPUs={self.gpu_count}")

    # ── Inference ─────────────────────────────────────────────────────────────

    def _build_prompt(self, messages: list[dict]) -> str:
        if self._tokenizer and hasattr(self._tokenizer, "apply_chat_template"):
            return self._tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        parts = []
        for m in messages:
            role    = m.get("role", "user")
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
            text       = outputs[0].outputs[0].text
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
            text       = out[0]["generated_text"]
            tokens_out = len(text.split())

        total     = (time.perf_counter() - t0) * 1000
        tokens_in = len(prompt.split())
        return InferResult(
            request_id=request_id,
            text=text,
            model_id=req.model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            ttft_ms=total * 0.1,
            total_ms=total,
            finish_reason="stop",
        )

    async def stream(self, req: InferRequest) -> AsyncIterator[str]:
        if self._backend == "vllm":
            result = await self.generate(req)
            yield result.text
            return

        from transformers import TextIteratorStreamer
        import threading

        prompt   = self._build_prompt(req.messages)
        streamer = TextIteratorStreamer(
            self._tokenizer, skip_special_tokens=True, skip_prompt=True
        )
        inputs = self._tokenizer(prompt, return_tensors="pt")

        # Move inputs to first GPU
        if self.device == "cuda":
            import torch
            inputs = {k: v.to("cuda:0") for k, v in inputs.items()}

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
        try:
            import torch
            if hasattr(self, "_pipe")  and self._pipe:  del self._pipe
            if hasattr(self, "_vllm")  and self._vllm:  del self._vllm
            if self.device == "cuda":
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        except Exception:
            pass
        self.loaded = False


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_max_memory(gpu_count: int) -> dict:
    """
    Build max_memory dict for transformers: uses 90% of each GPU's VRAM.
    This tells HF Accelerate to spread the model across ALL GPUs evenly.
    """
    gpus = _gpu_info()
    mem: dict = {}
    if gpus:
        for g in gpus:
            # Reserve 10% headroom per GPU
            usable = int(g["vram_mb"] * 0.90)
            mem[g["index"]] = f"{usable}MiB"
    else:
        for i in range(gpu_count):
            mem[i] = "90%"
    mem["cpu"] = "32GiB"  # CPU offload as final fallback
    return mem
