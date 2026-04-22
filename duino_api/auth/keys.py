"""
Duino API — API Key Management (v2)
Full lifecycle: generate, hash, validate, revoke, list, update.
Default TTL: 90 hours (324000 seconds).
Supports per-key project labels and usage counters.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Optional

import redis.asyncio as aioredis

from duino_api.config import settings

PREFIX           = "nxs_"
KEY_STORE_PREFIX = "apikey:"
KEY_INDEX_PREFIX = "apikey_idx:"   # owner → [key_hash, ...]

# Default expiry: 90 hours
DEFAULT_TTL_SECONDS = 90 * 3600   # 324 000 s


@dataclass
class APIKey:
    key_id:      str
    key_hash:    str           # SHA-256 of raw key — never store raw
    name:        str
    owner_id:    str
    quota_tier:  str           # "free" | "pro" | "enterprise"
    created_at:  float         # Unix timestamp
    expires_at:  float | None  # None = never; default = created_at + 90h
    is_active:   bool = True
    scopes:      list[str] = field(default_factory=lambda: ["inference:read", "inference:write"])
    projects:    list[str] = field(default_factory=list)   # project labels
    usage_count: int = 0       # incremented on every successful validate
    description: str = ""

    # ── Computed helpers ──────────────────────────────────────────────────────

    def expires_in_seconds(self) -> float | None:
        if self.expires_at is None:
            return None
        return max(0.0, self.expires_at - time.time())

    def expires_in_human(self) -> str:
        secs = self.expires_in_seconds()
        if secs is None:
            return "never"
        if secs <= 0:
            return "expired"
        h, r = divmod(int(secs), 3600)
        m, s = divmod(r, 60)
        return f"{h}h {m}m {s}s"

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def safe_dict(self) -> dict:
        """Return dict safe to send to client (no key_hash)."""
        d = asdict(self)
        d.pop("key_hash", None)
        d["expires_in"] = self.expires_in_human()
        d["is_expired"]  = self.is_expired()
        return d


# ─── Generation ───────────────────────────────────────────────────────────────

def generate_key(env: str = "prod") -> tuple[str, str]:
    """Return (raw_key, key_hash). Store ONLY the hash."""
    raw    = f"{PREFIX}{env}_{secrets.token_urlsafe(40)}"
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def constant_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def make_api_key(
    name:             str,
    owner_id:         str       = "",
    quota_tier:       str       = "free",
    expires_in_hours: float     = 90.0,   # default 90h
    projects:         list[str] = None,
    description:      str       = "",
    env:              str       = "prod",
) -> tuple[str, "APIKey"]:
    """
    Create a new APIKey object + return the raw key string.
    Returns: (raw_key, APIKey)
    """
    raw, hashed = generate_key(env)
    now     = time.time()
    exp     = now + expires_in_hours * 3600 if expires_in_hours > 0 else None
    key_obj = APIKey(
        key_id      = str(uuid.uuid4()),
        key_hash    = hashed,
        name        = name,
        owner_id    = owner_id or str(uuid.uuid4()),
        quota_tier  = quota_tier,
        created_at  = now,
        expires_at  = exp,
        projects    = projects or [],
        description = description,
    )
    return raw, key_obj


# ─── Redis-backed store ───────────────────────────────────────────────────────

class APIKeyStore:
    def __init__(self, redis: aioredis.Redis):
        self._r = redis

    async def save(self, key: APIKey, raw_key: str | None = None) -> None:
        payload = json.dumps(asdict(key))
        ttl     = None
        if key.expires_at:
            ttl = max(1, int(key.expires_at - time.time()))
        rkey = f"{KEY_STORE_PREFIX}{key.key_hash}"
        if ttl:
            await self._r.setex(rkey, ttl, payload)
        else:
            await self._r.set(rkey, payload)
        # Index: owner_id → key_hash set
        await self._r.sadd(f"{KEY_INDEX_PREFIX}{key.owner_id}", key.key_hash)

    async def get_by_hash(self, key_hash: str) -> APIKey | None:
        raw = await self._r.get(f"{KEY_STORE_PREFIX}{key_hash}")
        if not raw:
            return None
        return APIKey(**json.loads(raw))

    async def validate(self, raw_key: str) -> APIKey | None:
        if not raw_key.startswith(PREFIX):
            return None
        kh  = hash_key(raw_key)
        key = await self.get_by_hash(kh)
        if not key or not key.is_active:
            return None
        if key.is_expired():
            return None
        # Increment usage counter (fire-and-forget)
        key.usage_count += 1
        await self._r.set(
            f"{KEY_STORE_PREFIX}{kh}",
            json.dumps(asdict(key)),
        )
        return key

    async def revoke(self, key_hash: str) -> bool:
        rkey = f"{KEY_STORE_PREFIX}{key_hash}"
        raw  = await self._r.get(rkey)
        if not raw:
            return False
        data = json.loads(raw)
        data["is_active"] = False
        await self._r.set(rkey, json.dumps(data))
        return True

    async def update(self, key_hash: str, **fields) -> APIKey | None:
        """Update mutable fields: name, description, projects, quota_tier, expires_at."""
        rkey = f"{KEY_STORE_PREFIX}{key_hash}"
        raw  = await self._r.get(rkey)
        if not raw:
            return None
        data = json.loads(raw)
        allowed = {"name", "description", "projects", "quota_tier",
                   "expires_at", "is_active"}
        for k, v in fields.items():
            if k in allowed:
                data[k] = v
        await self._r.set(rkey, json.dumps(data))
        return APIKey(**data)

    async def list_by_owner(self, owner_id: str) -> list[APIKey]:
        members = await self._r.smembers(f"{KEY_INDEX_PREFIX}{owner_id}")
        keys: list[APIKey] = []
        for kh in members:
            raw = await self._r.get(f"{KEY_STORE_PREFIX}{kh}")
            if raw:
                keys.append(APIKey(**json.loads(raw)))
        return sorted(keys, key=lambda k: k.created_at, reverse=True)

    async def list_all(self) -> list[APIKey]:
        keys: list[APIKey] = []
        async for k in self._r.scan_iter(f"{KEY_STORE_PREFIX}*"):
            raw = await self._r.get(k)
            if raw:
                keys.append(APIKey(**json.loads(raw)))
        return sorted(keys, key=lambda k: k.created_at, reverse=True)


# ─── In-memory fallback (no Redis) ────────────────────────────────────────────

class InMemoryKeyStore:
    """Used when Redis is unavailable (single-user notebook mode)."""

    def __init__(self):
        self._store: dict[str, APIKey] = {}

    async def save(self, key: APIKey, raw_key: str | None = None) -> None:
        self._store[key.key_hash] = key

    async def get_by_hash(self, key_hash: str) -> APIKey | None:
        return self._store.get(key_hash)

    async def validate(self, raw_key: str) -> APIKey | None:
        if not raw_key.startswith(PREFIX):
            return None
        kh  = hash_key(raw_key)
        key = self._store.get(kh)
        if not key or not key.is_active:
            return None
        if key.is_expired():
            return None
        key.usage_count += 1
        return key

    async def revoke(self, key_hash: str) -> bool:
        key = self._store.get(key_hash)
        if not key:
            return False
        key.is_active = False
        return True

    async def update(self, key_hash: str, **fields) -> APIKey | None:
        key = self._store.get(key_hash)
        if not key:
            return None
        allowed = {"name", "description", "projects", "quota_tier",
                   "expires_at", "is_active"}
        for k, v in fields.items():
            if k in allowed:
                setattr(key, k, v)
        return key

    async def list_by_owner(self, owner_id: str) -> list[APIKey]:
        return sorted(
            [k for k in self._store.values() if k.owner_id == owner_id],
            key=lambda k: k.created_at, reverse=True,
        )

    async def list_all(self) -> list[APIKey]:
        return sorted(self._store.values(), key=lambda k: k.created_at, reverse=True)
