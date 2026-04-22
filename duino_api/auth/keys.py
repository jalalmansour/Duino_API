"""
Duino API — API Key Management
Generates, hashes, validates, and revokes API keys.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import asdict, dataclass
from typing import Optional

import redis.asyncio as aioredis

from duino_api.config import settings

PREFIX = "nxs_"
KEY_STORE_PREFIX = "apikey:"


@dataclass
class APIKey:
    key_id: str
    key_hash: str          # SHA-256 of raw key — never store raw
    name: str
    owner_id: str
    quota_tier: str        # "free" | "pro" | "enterprise"
    created_at: float      # Unix timestamp
    expires_at: float | None
    is_active: bool = True
    scopes: list[str] = None  # type: ignore

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ["inference:read", "inference:write"]


# ─── Generation ──────────────────────────────────────────────────────────────

def generate_key(env: str = "prod") -> tuple[str, str]:
    """Return (raw_key, key_hash). Store ONLY the hash."""
    raw = f"{PREFIX}{env}_{secrets.token_urlsafe(40)}"
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def constant_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


# ─── Redis-backed store ───────────────────────────────────────────────────────

class APIKeyStore:
    def __init__(self, redis: aioredis.Redis):
        self._r = redis

    async def save(self, key: APIKey) -> None:
        payload = json.dumps(asdict(key))
        ttl = None
        if key.expires_at:
            ttl = max(1, int(key.expires_at - time.time()))
        rkey = f"{KEY_STORE_PREFIX}{key.key_hash}"
        if ttl:
            await self._r.setex(rkey, ttl, payload)
        else:
            await self._r.set(rkey, payload)

    async def get_by_hash(self, key_hash: str) -> APIKey | None:
        raw = await self._r.get(f"{KEY_STORE_PREFIX}{key_hash}")
        if not raw:
            return None
        data = json.loads(raw)
        return APIKey(**data)

    async def validate(self, raw_key: str) -> APIKey | None:
        if not raw_key.startswith(PREFIX):
            return None
        kh = hash_key(raw_key)
        key = await self.get_by_hash(kh)
        if not key or not key.is_active:
            return None
        if key.expires_at and key.expires_at < time.time():
            return None
        return key

    async def revoke(self, key_hash: str) -> bool:
        rkey = f"{KEY_STORE_PREFIX}{key_hash}"
        raw = await self._r.get(rkey)
        if not raw:
            return False
        data = json.loads(raw)
        data["is_active"] = False
        await self._r.set(rkey, json.dumps(data))
        return True

    async def list_by_owner(self, owner_id: str) -> list[APIKey]:
        """Scan all keys for a given owner (dev/admin use)."""
        keys: list[APIKey] = []
        async for k in self._r.scan_iter(f"{KEY_STORE_PREFIX}*"):
            raw = await self._r.get(k)
            if raw:
                data = json.loads(raw)
                if data.get("owner_id") == owner_id:
                    keys.append(APIKey(**data))
        return keys


# ─── In-memory fallback (no Redis) ────────────────────────────────────────────

class InMemoryKeyStore:
    """Used when Redis is unavailable (single-user notebook mode)."""

    def __init__(self):
        self._store: dict[str, APIKey] = {}

    async def save(self, key: APIKey) -> None:
        self._store[key.key_hash] = key

    async def get_by_hash(self, key_hash: str) -> APIKey | None:
        return self._store.get(key_hash)

    async def validate(self, raw_key: str) -> APIKey | None:
        if not raw_key.startswith(PREFIX):
            return None
        kh = hash_key(raw_key)
        key = self._store.get(kh)
        if not key or not key.is_active:
            return None
        if key.expires_at and key.expires_at < time.time():
            return None
        return key

    async def revoke(self, key_hash: str) -> bool:
        key = self._store.get(key_hash)
        if not key:
            return False
        key.is_active = False
        return True

    async def list_by_owner(self, owner_id: str) -> list[APIKey]:
        return [k for k in self._store.values() if k.owner_id == owner_id]
