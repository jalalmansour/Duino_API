"""
Duino API — FastAPI Application
Main gateway: auth, quota, inference routes, session routes, health.
"""
from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from duino_api.auth.keys import (
    APIKey, APIKeyStore, InMemoryKeyStore,
    generate_key, hash_key, make_api_key,
    DEFAULT_TTL_SECONDS,
)
from duino_api.auth.quota import (
    TIERS, InMemoryRateLimiter, RateLimitExceeded, RedisRateLimiter,
)
from duino_api.config import settings
from duino_api.inference.engine import GEMMA4_MODELS, InferRequest, InferenceEngine
from duino_api.sessions.manager import InMemorySessionManager, RedisSessionManager

# ─── App State ────────────────────────────────────────────────────────────────

class _State:
    engine: InferenceEngine | None = None
    key_store: APIKeyStore | InMemoryKeyStore = InMemoryKeyStore()
    rate_limiter: RedisRateLimiter | InMemoryRateLimiter = InMemoryRateLimiter()
    session_mgr: RedisSessionManager | InMemorySessionManager = InMemorySessionManager()
    redis: aioredis.Redis | None = None
    start_time: float = time.time()
    url_created_at: float = time.time()   # tracks when public URL was generated
    api_url: str = ""                      # stored at startup for expiry display
    ui_url: str  = ""


state = _State()


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    # Connect Redis (non-fatal if unavailable)
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        state.redis = r
        state.key_store = APIKeyStore(r)
        state.rate_limiter = RedisRateLimiter(r)
        state.session_mgr = RedisSessionManager(r)
        print("✅  Redis connected")
    except Exception as exc:
        print(f"⚠️  Redis unavailable ({exc}) — using in-memory fallback")

    # Load inference engine
    from duino_api.adapters.detector import EnvironmentDetector
    adapter = EnvironmentDetector.get()
    caps = adapter.capabilities()
    cfg = GEMMA4_MODELS.get(settings.default_model)
    if cfg:
        cfg.quant = cfg.quant or caps.recommended_quant
        engine = InferenceEngine(cfg, quant=cfg.quant)
        try:
            engine.load()
            state.engine = engine
            print(f"✅  Model loaded: {cfg.hf_name} ({cfg.quant or 'no quant'})")
        except Exception as exc:
            print(f"⚠️  Model load failed: {exc} — inference disabled")

    yield

    # --- SHUTDOWN ---
    if state.engine:
        state.engine.unload()
    if state.redis:
        await state.redis.aclose()


# ─── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Duino API — Hyperscale Inference Platform",
    version="1.0.0",
    description="Cloud-agnostic AI inference · Gemma 4 · Session-aware · HTTPS",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Auth dependency ──────────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    raw_key: str | None = Security(_api_key_header),
) -> APIKey:
    if not raw_key:
        raise HTTPException(401, detail="X-API-Key header required")
    key = await state.key_store.validate(raw_key)
    if not key:
        raise HTTPException(403, detail="Invalid or expired API key")
    return key


async def enforce_quota(api_key: APIKey = Depends(require_api_key)) -> APIKey:
    tier = TIERS.get(api_key.quota_tier, TIERS["free"])
    try:
        await state.rate_limiter.check(api_key.key_id, tier)
    except RateLimitExceeded as exc:
        raise HTTPException(
            429,
            detail={"error": "rate_limit_exceeded", "window": exc.window,
                    "limit": exc.limit, "current": exc.current},
        )
    return api_key


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str = Field(..., max_length=100_000)


class ChatRequest(BaseModel):
    model: str = Field("gemma-4-2b", max_length=64)
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=100)
    max_tokens: int = Field(512, ge=1, le=8192)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    top_p: float = Field(0.95, ge=0.0, le=1.0)
    stream: bool = False
    session_id: str | None = None


class KeyCreateRequest(BaseModel):
    name:             str        = Field(..., max_length=128)
    quota_tier:       str        = Field("free", pattern="^(free|pro|enterprise)$")
    expires_in_hours: float      = Field(90.0, ge=1.0, le=8760.0)  # default 90h, max 1 year
    projects:         list[str]  = Field(default_factory=list)
    description:      str        = Field("", max_length=256)


class KeyUpdateRequest(BaseModel):
    name:             str | None       = None
    description:      str | None       = None
    projects:         list[str] | None = None
    quota_tier:       str | None       = None
    expires_in_hours: float | None     = None   # re-set expiry from now


class SessionCreateRequest(BaseModel):
    model_id: str = Field("gemma-4-2b", max_length=64)


# ─── Routes: Inference ────────────────────────────────────────────────────────

@app.post("/v1/chat/completions")
async def chat_completions(
    req: ChatRequest,
    api_key: APIKey = Depends(enforce_quota),
):
    if not state.engine or not state.engine.loaded:
        raise HTTPException(503, detail="Inference engine not available")

    msgs = [m.model_dump() for m in req.messages]

    # Session context injection
    if req.session_id:
        session = await state.session_mgr.get(req.session_id, api_key.owner_id)
        if session:
            msgs = session.messages + msgs

    infer_req = InferRequest(
        messages=msgs,
        model_id=req.model,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
        top_p=req.top_p,
        stream=req.stream,
        session_id=req.session_id,
    )

    if req.stream:
        async def _gen():
            async for token in state.engine.stream(infer_req):
                chunk = {
                    "id": "chatcmpl-stream",
                    "object": "chat.completion.chunk",
                    "choices": [{"delta": {"content": token}, "index": 0}],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_gen(), media_type="text/event-stream")

    result = await state.engine.generate(infer_req)

    # Persist to session
    if req.session_id:
        for m in msgs:
            await state.session_mgr.append_message(req.session_id, api_key.owner_id, m)
        await state.session_mgr.append_message(
            req.session_id, api_key.owner_id,
            {"role": "assistant", "content": result.text},
        )

    return {
        "id": result.request_id,
        "object": "chat.completion",
        "model": result.model_id,
        "choices": [{"message": {"role": "assistant", "content": result.text},
                     "finish_reason": result.finish_reason, "index": 0}],
        "usage": {"prompt_tokens": result.tokens_in,
                  "completion_tokens": result.tokens_out,
                  "total_tokens": result.tokens_in + result.tokens_out},
    }


@app.get("/v1/models")
async def list_models(api_key: APIKey = Depends(require_api_key)):
    return {"data": [
        {"id": k, "object": "model", "owned_by": "duino-api"}
        for k in GEMMA4_MODELS
    ]}


# ─── Routes: Sessions ─────────────────────────────────────────────────────────

@app.post("/v1/sessions")
async def create_session(
    req: SessionCreateRequest,
    api_key: APIKey = Depends(require_api_key),
):
    s = await state.session_mgr.create(api_key.owner_id, req.model_id)
    return {"session_id": s.id, "model_id": s.model_id, "created_at": s.created_at}


@app.get("/v1/sessions/{session_id}")
async def get_session(
    session_id: str,
    api_key: APIKey = Depends(require_api_key),
):
    s = await state.session_mgr.get(session_id, api_key.owner_id)
    if not s:
        raise HTTPException(404, detail="Session not found")
    return s


@app.delete("/v1/sessions/{session_id}")
async def delete_session(
    session_id: str,
    api_key: APIKey = Depends(require_api_key),
):
    ok = await state.session_mgr.delete(session_id, api_key.owner_id)
    if not ok:
        raise HTTPException(404, detail="Session not found")
    return {"deleted": True}


# ─── Routes: API Keys ─────────────────────────────────────────────────────────

@app.post("/v1/keys")
async def create_key(req: KeyCreateRequest):
    """Create a new API key. Default TTL = 90 hours."""
    raw, key = make_api_key(
        name             = req.name,
        quota_tier       = req.quota_tier,
        expires_in_hours = req.expires_in_hours,
        projects         = req.projects,
        description      = req.description,
    )
    await state.key_store.save(key, raw_key=raw)
    info = key.safe_dict()
    info["api_key"] = raw   # only time raw key is exposed
    info["message"] = "Store this key securely — it will NOT be shown again."
    return info


@app.get("/v1/keys")
async def list_keys(api_key: APIKey = Depends(require_api_key)):
    """List all API keys (owner-scoped or all for admin)."""
    keys = await state.key_store.list_all()
    return {"keys": [k.safe_dict() for k in keys], "total": len(keys)}


@app.delete("/v1/keys/{key_id}")
async def delete_key(
    key_id: str,
    api_key: APIKey = Depends(require_api_key),
):
    """Revoke an API key by key_id."""
    # Find key by key_id (scan all)
    all_keys = await state.key_store.list_all()
    target = next((k for k in all_keys if k.key_id == key_id), None)
    if not target:
        raise HTTPException(404, detail="Key not found")
    await state.key_store.revoke(target.key_hash)
    return {"revoked": True, "key_id": key_id}


@app.patch("/v1/keys/{key_id}")
async def update_key(
    key_id: str,
    req: KeyUpdateRequest,
    api_key: APIKey = Depends(require_api_key),
):
    """Update name, description, projects, quota_tier, or extend expiry."""
    all_keys = await state.key_store.list_all()
    target = next((k for k in all_keys if k.key_id == key_id), None)
    if not target:
        raise HTTPException(404, detail="Key not found")
    fields: dict = {}
    if req.name        is not None: fields["name"]        = req.name
    if req.description is not None: fields["description"] = req.description
    if req.projects    is not None: fields["projects"]    = req.projects
    if req.quota_tier  is not None: fields["quota_tier"]  = req.quota_tier
    if req.expires_in_hours is not None:
        fields["expires_at"] = time.time() + req.expires_in_hours * 3600
    updated = await state.key_store.update(target.key_hash, **fields)
    return updated.safe_dict() if updated else {"error": "update failed"}


# ─── Routes: URL Expiry ───────────────────────────────────────────────────────

@app.get("/v1/url/expiry")
async def url_expiry():
    """Returns countdown until the public Colab proxy URLs expire (90h window)."""
    ttl = DEFAULT_TTL_SECONDS
    elapsed  = time.time() - state.url_created_at
    remaining = max(0.0, ttl - elapsed)
    h, r = divmod(int(remaining), 3600)
    m, s = divmod(r, 60)
    return {
        "url_created_at":   state.url_created_at,
        "ttl_seconds":      ttl,
        "elapsed_seconds":  round(elapsed),
        "remaining_seconds": round(remaining),
        "expires_in":       f"{h:02d}h {m:02d}m {s:02d}s",
        "is_expired":       remaining <= 0,
        "api_url":          state.api_url,
        "ui_url":           state.ui_url,
    }


# ─── Routes: Health ───────────────────────────────────────────────────────────

@app.get("/v1/health")
async def health():
    from duino_api.adapters.detector import EnvironmentDetector
    caps    = EnvironmentDetector.get().capabilities()
    elapsed = time.time() - state.url_created_at
    url_remaining = max(0.0, DEFAULT_TTL_SECONDS - elapsed)
    h, r = divmod(int(url_remaining), 3600)
    m, s = divmod(r, 60)
    return {
        "status":         "ok",
        "uptime_seconds": round(time.time() - state.start_time),
        "model_loaded":   state.engine.loaded if state.engine else False,
        "redis_connected": state.redis is not None,
        "environment":    caps.runtime.value,
        "gpu":            caps.gpu_name,
        "gpu_vram_mb":    caps.gpu_vram_mb,
        "url_expires_in": f"{h:02d}h {m:02d}m {s:02d}s",
        "url_remaining_seconds": round(url_remaining),
    }
