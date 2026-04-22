"""
Duino API — Core Configuration
Loads settings from environment variables / .env file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=False)


@dataclass
class Settings:
    # ── Server ────────────────────────────────────────────────────────────
    host: str = field(default_factory=lambda: os.getenv("DUINO_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("DUINO_PORT", "8000")))
    env: str = field(default_factory=lambda: os.getenv("DUINO_ENV", "development"))
    secret_key: str = field(
        default_factory=lambda: os.getenv("DUINO_SECRET_KEY", "dev-secret-key")
    )

    # ── Model ─────────────────────────────────────────────────────────────
    default_model: str = field(
        default_factory=lambda: os.getenv("DEFAULT_MODEL", "gemma-4-2b")
    )
    hf_token: str | None = field(default_factory=lambda: os.getenv("HF_TOKEN"))
    hf_home: str = field(default_factory=lambda: os.getenv("HF_HOME", "/tmp/hf_cache"))

    # ── Redis ─────────────────────────────────────────────────────────────
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379")
    )
    redis_password: str | None = field(
        default_factory=lambda: os.getenv("REDIS_PASSWORD") or None
    )
    session_ttl: int = field(
        default_factory=lambda: int(os.getenv("SESSION_TTL_SECONDS", "86400"))
    )

    # ── Tunneling ─────────────────────────────────────────────────────────
    ngrok_token: str | None = field(
        default_factory=lambda: os.getenv("NGROK_AUTHTOKEN")
    )
    cf_tunnel_token: str | None = field(
        default_factory=lambda: os.getenv("CF_TUNNEL_TOKEN")
    )

    # ── Quota ─────────────────────────────────────────────────────────────
    quota_free_rpm: int = field(
        default_factory=lambda: int(os.getenv("QUOTA_FREE_RPM", "10"))
    )
    quota_free_daily: int = field(
        default_factory=lambda: int(os.getenv("QUOTA_FREE_DAILY", "500"))
    )
    quota_pro_rpm: int = field(
        default_factory=lambda: int(os.getenv("QUOTA_PRO_RPM", "60"))
    )
    quota_pro_daily: int = field(
        default_factory=lambda: int(os.getenv("QUOTA_PRO_DAILY", "10000"))
    )
    quota_ent_rpm: int = field(
        default_factory=lambda: int(os.getenv("QUOTA_ENT_RPM", "300"))
    )
    quota_ent_daily: int = field(
        default_factory=lambda: int(os.getenv("QUOTA_ENT_DAILY", "100000"))
    )

    # ── UI ────────────────────────────────────────────────────────────────
    ui_port: int = field(default_factory=lambda: int(os.getenv("UI_PORT", "3000")))
    ui_build_dir: str = field(
        default_factory=lambda: os.getenv("UI_BUILD_DIR", "ui/dist")
    )

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        return self.env == "development"


# Singleton
settings = Settings()
