"""
Duino API — Session Manager
Distributed sessions backed by Redis; in-memory fallback for notebooks.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field

from duino_api.config import settings


@dataclass
class Session:
    id: str
    owner_id: str
    tenant_id: str | None
    model_id: str
    created_at: float
    last_accessed: float
    expires_at: float
    messages: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    token_count: int = 0


SESSION_PREFIX = "session:"


def _new_session(owner_id: str, model_id: str, tenant_id: str | None = None) -> Session:
    now = time.time()
    return Session(
        id=str(uuid.uuid4()),
        owner_id=owner_id,
        tenant_id=tenant_id,
        model_id=model_id,
        created_at=now,
        last_accessed=now,
        expires_at=now + settings.session_ttl,
    )


class RedisSessionManager:
    def __init__(self, redis):
        self._r = redis

    async def create(
        self, owner_id: str, model_id: str, tenant_id: str | None = None
    ) -> Session:
        s = _new_session(owner_id, model_id, tenant_id)
        await self._save(s)
        return s

    async def get(self, session_id: str, owner_id: str) -> Session | None:
        raw = await self._r.get(f"{SESSION_PREFIX}{session_id}")
        if not raw:
            return None
        data = json.loads(raw)
        s = Session(**data)
        if s.owner_id != owner_id:
            return None  # tenant isolation
        if s.expires_at < time.time():
            await self.delete(session_id, owner_id)
            return None
        s.last_accessed = time.time()
        await self._save(s)
        return s

    async def append_message(self, session_id: str, owner_id: str, message: dict) -> Session | None:
        s = await self.get(session_id, owner_id)
        if not s:
            return None
        s.messages.append(message)
        s.token_count += len(message.get("content", "").split())
        await self._save(s)
        return s

    async def delete(self, session_id: str, owner_id: str) -> bool:
        raw = await self._r.get(f"{SESSION_PREFIX}{session_id}")
        if not raw:
            return False
        data = json.loads(raw)
        if data.get("owner_id") != owner_id:
            return False
        await self._r.delete(f"{SESSION_PREFIX}{session_id}")
        return True

    async def _save(self, s: Session) -> None:
        ttl = max(1, int(s.expires_at - time.time()))
        await self._r.setex(
            f"{SESSION_PREFIX}{s.id}", ttl, json.dumps(asdict(s))
        )


class InMemorySessionManager:
    """Notebook-mode fallback."""

    def __init__(self):
        self._store: dict[str, Session] = {}

    async def create(
        self, owner_id: str, model_id: str, tenant_id: str | None = None
    ) -> Session:
        s = _new_session(owner_id, model_id, tenant_id)
        self._store[s.id] = s
        return s

    async def get(self, session_id: str, owner_id: str) -> Session | None:
        s = self._store.get(session_id)
        if not s or s.owner_id != owner_id:
            return None
        if s.expires_at < time.time():
            del self._store[session_id]
            return None
        s.last_accessed = time.time()
        return s

    async def append_message(self, session_id: str, owner_id: str, message: dict) -> Session | None:
        s = await self.get(session_id, owner_id)
        if not s:
            return None
        s.messages.append(message)
        s.token_count += len(message.get("content", "").split())
        return s

    async def delete(self, session_id: str, owner_id: str) -> bool:
        s = self._store.get(session_id)
        if not s or s.owner_id != owner_id:
            return False
        del self._store[session_id]
        return True
