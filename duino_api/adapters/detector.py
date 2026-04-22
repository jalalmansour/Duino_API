"""
Duino API — Environment Adapter Base + Detector
Abstracts all runtime differences between notebook/cloud environments.
"""
from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class RuntimeEnv(str, Enum):
    COLAB = "google_colab"
    KAGGLE = "kaggle"
    LIGHTNING = "lightning_ai"
    AWS = "aws_sagemaker"
    JUPYTER = "jupyter"
    DOCKER = "docker"
    BARE = "bare_metal"


@dataclass
class EnvCapabilities:
    runtime: RuntimeEnv
    gpu_available: bool = False
    gpu_name: str = "none"
    gpu_vram_mb: int = 0
    ram_gb: float = 4.0
    tunnel_required: bool = True
    persistent_storage: bool = False
    can_install_packages: bool = True
    can_run_subprocesses: bool = True
    recommended_quant: str | None = "bnb-4bit"


class RuntimeAdapter(ABC):
    """Interface every environment adapter must implement."""

    @abstractmethod
    def detect(self) -> bool: ...

    @abstractmethod
    def capabilities(self) -> EnvCapabilities: ...

    @abstractmethod
    def install(self, packages: list[str]) -> None: ...

    @abstractmethod
    def expose_port(self, port: int) -> str:
        """Return public HTTPS URL for the given port."""
        ...

    def gpu_device(self) -> str:
        caps = self.capabilities()
        return "cuda" if caps.gpu_available else "cpu"


# ─────────────────────────────────────────────────────────────────────────────
# Concrete adapters
# ─────────────────────────────────────────────────────────────────────────────

class ColabAdapter(RuntimeAdapter):
    def detect(self) -> bool:
        return "COLAB_GPU" in os.environ or os.path.exists("/content")

    def capabilities(self) -> EnvCapabilities:
        gpu = _probe_gpu()
        return EnvCapabilities(
            runtime=RuntimeEnv.COLAB,
            gpu_available=gpu["available"],
            gpu_name=gpu["name"],
            gpu_vram_mb=gpu["vram_mb"],
            ram_gb=_probe_ram(),
            tunnel_required=True,
            persistent_storage=False,
            recommended_quant=_recommend_quant(gpu["vram_mb"]),
        )

    def install(self, packages: list[str]) -> None:
        if packages:
            subprocess.run(["pip", "install", "-q", *packages], check=True)

    def expose_port(self, port: int) -> str:
        try:
            from google.colab.output import eval_js  # type: ignore
            url = eval_js(f"google.colab.kernel.proxyPort({port})")
            return str(url)
        except ImportError:
            return _ngrok_expose(port)


class KaggleAdapter(RuntimeAdapter):
    def detect(self) -> bool:
        return "KAGGLE_KERNEL_RUN_TYPE" in os.environ

    def capabilities(self) -> EnvCapabilities:
        gpu = _probe_gpu()
        return EnvCapabilities(
            runtime=RuntimeEnv.KAGGLE,
            gpu_available=gpu["available"],
            gpu_name=gpu["name"],
            gpu_vram_mb=gpu["vram_mb"],
            ram_gb=_probe_ram(),
            tunnel_required=True,
            persistent_storage=True,
            recommended_quant=_recommend_quant(gpu["vram_mb"]),
        )

    def install(self, packages: list[str]) -> None:
        if packages:
            subprocess.run(["pip", "install", "-q", *packages], check=True)

    def expose_port(self, port: int) -> str:
        return _ngrok_expose(port)


class LightningAdapter(RuntimeAdapter):
    def detect(self) -> bool:
        return "LIGHTNING_CLOUD_URL" in os.environ

    def capabilities(self) -> EnvCapabilities:
        gpu = _probe_gpu()
        return EnvCapabilities(
            runtime=RuntimeEnv.LIGHTNING,
            gpu_available=gpu["available"],
            gpu_name=gpu["name"],
            gpu_vram_mb=gpu["vram_mb"],
            ram_gb=_probe_ram(),
            tunnel_required=False,
            persistent_storage=True,
            recommended_quant=_recommend_quant(gpu["vram_mb"]),
        )

    def install(self, packages: list[str]) -> None:
        if packages:
            subprocess.run(["pip", "install", "-q", *packages], check=True)

    def expose_port(self, port: int) -> str:
        base = os.environ.get("LIGHTNING_CLOUD_URL", "http://localhost")
        return f"{base}/proxy/{port}"


class AWSAdapter(RuntimeAdapter):
    def detect(self) -> bool:
        return "SM_MODEL_DIR" in os.environ or "AWS_DEFAULT_REGION" in os.environ

    def capabilities(self) -> EnvCapabilities:
        gpu = _probe_gpu()
        return EnvCapabilities(
            runtime=RuntimeEnv.AWS,
            gpu_available=gpu["available"],
            gpu_name=gpu["name"],
            gpu_vram_mb=gpu["vram_mb"],
            ram_gb=_probe_ram(),
            tunnel_required=False,
            persistent_storage=True,
            recommended_quant=_recommend_quant(gpu["vram_mb"]),
        )

    def install(self, packages: list[str]) -> None:
        if packages:
            subprocess.run(["pip", "install", "-q", *packages], check=True)

    def expose_port(self, port: int) -> str:
        # In SageMaker, the endpoint URL is managed externally
        return f"http://localhost:{port}"


class JupyterAdapter(RuntimeAdapter):
    def detect(self) -> bool:
        return (
            "JUPYTERHUB_API_TOKEN" in os.environ
            or "JPY_PARENT_PID" in os.environ
            or os.path.exists("/usr/local/share/jupyter")
        )

    def capabilities(self) -> EnvCapabilities:
        gpu = _probe_gpu()
        return EnvCapabilities(
            runtime=RuntimeEnv.JUPYTER,
            gpu_available=gpu["available"],
            gpu_name=gpu["name"],
            gpu_vram_mb=gpu["vram_mb"],
            ram_gb=_probe_ram(),
            tunnel_required=True,
            persistent_storage=True,
            recommended_quant=_recommend_quant(gpu["vram_mb"]),
        )

    def install(self, packages: list[str]) -> None:
        if packages:
            subprocess.run(["pip", "install", "-q", *packages], check=True)

    def expose_port(self, port: int) -> str:
        return _ngrok_expose(port)


class BareMetalAdapter(RuntimeAdapter):
    def detect(self) -> bool:
        return True  # fallback

    def capabilities(self) -> EnvCapabilities:
        gpu = _probe_gpu()
        return EnvCapabilities(
            runtime=RuntimeEnv.BARE,
            gpu_available=gpu["available"],
            gpu_name=gpu["name"],
            gpu_vram_mb=gpu["vram_mb"],
            ram_gb=_probe_ram(),
            tunnel_required=False,
            persistent_storage=True,
            recommended_quant=_recommend_quant(gpu["vram_mb"]),
        )

    def install(self, packages: list[str]) -> None:
        if packages:
            subprocess.run(["pip", "install", "-q", *packages], check=True)

    def expose_port(self, port: int) -> str:
        return f"http://localhost:{port}"


# ─────────────────────────────────────────────────────────────────────────────
# Detector
# ─────────────────────────────────────────────────────────────────────────────

_ADAPTERS: list[type[RuntimeAdapter]] = [
    ColabAdapter,
    KaggleAdapter,
    LightningAdapter,
    AWSAdapter,
    JupyterAdapter,
    BareMetalAdapter,
]


class EnvironmentDetector:
    _cached: RuntimeAdapter | None = None

    @classmethod
    def get(cls) -> RuntimeAdapter:
        if cls._cached is None:
            for AdapterCls in _ADAPTERS:
                adapter = AdapterCls()
                if adapter.detect():
                    cls._cached = adapter
                    break
        return cls._cached  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _probe_gpu() -> dict:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            return {
                "available": True,
                "name": parts[0].strip(),
                "vram_mb": int(parts[1].strip()),
            }
    except Exception:
        pass
    return {"available": False, "name": "none", "vram_mb": 0}


def _probe_ram() -> float:
    try:
        import psutil
        return round(psutil.virtual_memory().total / 1e9, 1)
    except ImportError:
        return 8.0


def _recommend_quant(vram_mb: int) -> str | None:
    if vram_mb >= 40_000:
        return None
    if vram_mb >= 24_000:
        return "awq"
    if vram_mb >= 12_000:
        return "bnb-4bit"
    if vram_mb > 0:
        return "bnb-4bit"
    return None  # CPU — handled by model loading


def _ngrok_expose(port: int) -> str:
    from duino_api.config import settings  # late import
    try:
        from pyngrok import ngrok, conf
        if settings.ngrok_token:
            conf.get_default().auth_token = settings.ngrok_token
        tunnel = ngrok.connect(port, "http")
        url: str = tunnel.public_url  # type: ignore
        return url.replace("http://", "https://")
    except Exception as exc:
        return f"http://localhost:{port}  # ngrok failed: {exc}"
