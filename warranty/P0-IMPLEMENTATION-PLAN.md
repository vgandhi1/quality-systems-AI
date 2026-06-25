# P0 Implementation Plan — LAN-safe API hardening

**Goal:** Make `warranty-api` safe to expose on a shared LAN (WSL portproxy → Windows `192.*`) without open endpoints or accidental wide bind.

**Governance refs:** `governance/standards/07-SECURITY.md` (dev vs prod auth, CORS), `01-ENV-VARIABLES.md`

**Out of scope for P0:** rate limiting (T3), HTTPS (T3), LLM prompt delimiters (P1).

---

## P0 items (4)

| # | Item | Why |
|---|------|-----|
| P0-1 | Fail-closed auth in `production` | `07-SECURITY`: prod must reject if `WARRANTY_API_KEY` unset |
| P0-2 | Configurable bind host/port | Default `127.0.0.1` — avoid accidental LAN exposure |
| P0-3 | Auth required when bind is non-localhost | LAN bind without API key = open network |
| P0-4 | CORS allowlist | Browser clients on LAN cannot call API from arbitrary origins |

---

## Design

### Auth decision matrix

| `WARRANTY_ENVIRONMENT` | `WARRANTY_API_HOST` | `WARRANTY_API_KEY` | Protected routes |
|------------------------|---------------------|--------------------|------------------|
| `development` | `127.0.0.1` | unset | **Open** (localhost dev) |
| `development` | `0.0.0.0` | unset | **503** — refuse to start or reject all protected routes |
| `development` | `0.0.0.0` | set | Require `X-API-Key` |
| `production` | any | unset | **503** on startup — service misconfigured |
| `production` | any | set | Require `X-API-Key` |

**Public paths (no key):** `/health`, `/docs`, `/redoc`, `/openapi.json`  
**New:** `GET /` → redirect to `/docs` (UX; not security)

**Protected paths:** everything else (`/adjudicate/*`, `/escalate/*`, `/claim-state`)

### Startup validation (`config.py`)

```python
def auth_required() -> bool:
    """True when API key must be presented on protected routes."""
    if ENVIRONMENT == "production":
        return True
    return API_HOST not in ("127.0.0.1", "localhost")

def validate_api_config() -> None:
    if ENVIRONMENT == "production" and not API_KEY:
        raise SystemExit("WARRANTY_API_KEY required when WARRANTY_ENVIRONMENT=production")
    if auth_required() and not API_KEY:
        raise SystemExit(
            "WARRANTY_API_KEY required when binding to a non-localhost host "
            f"({API_HOST}). See DEV-LAN-ACCESS.md."
        )
```

Call `validate_api_config()` from `api.run()` before uvicorn starts.

### Middleware refactor (`api.py`)

Replace `optional_api_key_guard` with `api_key_guard`:

1. If path is public → pass through  
2. If `not auth_required()` and no `API_KEY` → pass through (localhost dev)  
3. If `auth_required()` or `API_KEY` set → validate `X-API-Key` with `hmac.compare_digest`  
4. On failure → `401` with generic message (no key hints)

`/health` response includes `environment` from config (not hardcoded `"development"`).

### CORS (`api.py`)

```python
from fastapi.middleware.cors import CORSMiddleware

# WARRANTY_CORS_ORIGINS=http://localhost:3000,http://192.168.1.10:3000
# Empty / unset → no CORS middleware (non-browser clients only)
```

| `WARRANTY_CORS_ORIGINS` | Behavior |
|-------------------------|----------|
| unset or empty | No `CORSMiddleware` added |
| comma-separated URLs | `allow_origins=...`, `allow_methods=["GET","POST"]`, `allow_headers=["X-API-Key","Content-Type"]` |

Do not use `allow_origins=["*"]` with credentials.

### Bind host/port (`config.py` + `api.run()`)

```python
API_HOST = os.environ.get("WARRANTY_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("WARRANTY_API_PORT", "8080"))
```

```python
uvicorn.run("warranty.api:app", host=API_HOST, port=API_PORT, reload=False)
```

**LAN access workflow** (document in `.env.example`):

```bash
WARRANTY_API_HOST=0.0.0.0
WARRANTY_API_KEY=<strong-random-key>
# WARRANTY_CORS_ORIGINS=http://192.168.1.50:3000
```

---

## Files to change

| File | Changes |
|------|---------|
| `src/warranty/config.py` | `API_HOST`, `API_PORT`, `CORS_ORIGINS`, `auth_required()`, `validate_api_config()` |
| `src/warranty/api.py` | Auth middleware, CORS, `GET /` redirect, call validation in `run()`, dynamic `environment` in `/health` |
| `.env.example` | Document P0 vars with LAN comments |
| `DEV-LAN-ACCESS.md` | Update env block to match new defaults |
| `README.md` | Note localhost default + LAN env vars |
| `plan.md` | Mark P0 items done after merge |
| `tests/test_api.py` | Extend with auth/CORS/redirect tests |
| `tests/test_config.py` | **New** — `auth_required`, `validate_api_config` |

---

## Test plan

### `tests/test_config.py`

| Test | Expect |
|------|--------|
| `auth_required` prod always true | `ENVIRONMENT=production` → True |
| `auth_required` dev localhost false | `127.0.0.1` → False |
| `auth_required` dev 0.0.0.0 true | `0.0.0.0` → True |
| `validate_api_config` prod no key | `SystemExit` |
| `validate_api_config` lan bind no key | `SystemExit` |
| `validate_api_config` dev localhost no key | passes |

Use `monkeypatch.setenv` — no `.env` file in tests.

### `tests/test_api.py`

| Test | Expect |
|------|--------|
| `GET /` | `307` or `302` → `/docs` |
| `/health` includes `environment` | matches env |
| Protected route + key required + no header | `401` |
| Protected route + valid `X-API-Key` | `200` |
| Public `/health` without key when key required | `200` |
| CORS preflight (if origins set) | `Access-Control-Allow-Origin` present for allowed origin |

Mock pattern for API key tests:

```python
@pytest.fixture
def client_with_key(monkeypatch):
    monkeypatch.setenv("WARRANTY_API_KEY", "test-secret-key")
    monkeypatch.setenv("WARRANTY_API_HOST", "0.0.0.0")
    # Re-import or use app factory if module-level config is cached
```

**Note:** If config is read at import time, either:
- (A) refactor to `get_config()` function read per request, or  
- (B) use `importlib.reload` in tests, or  
- (C) add `create_app()` factory called at TestClient setup  

**Recommendation:** add `create_app() -> FastAPI` in `api.py`; module-level `app = create_app()` for uvicorn; tests call `create_app()` after `monkeypatch` for isolation.

---

## Implementation order

```text
1. config.py     — API_HOST/PORT, CORS_ORIGINS, auth helpers, validate_api_config
2. api.py        — create_app(), middleware, / redirect, run() validation
3. .env.example  — document vars
4. test_config.py
5. test_api.py   — extend auth + redirect
6. docs          — DEV-LAN-ACCESS.md, README.md, plan.md status
7. pytest + ruff — must pass; no CI workflow change needed
```

**Estimated diff:** ~250 lines across 8 files.

---

## Acceptance criteria

- [ ] Default `uv run warranty-api` binds **`127.0.0.1:8080`** only (not reachable from LAN without explicit host change)
- [ ] `WARRANTY_API_HOST=0.0.0.0` without `WARRANTY_API_KEY` → **startup fails** with clear message
- [ ] `WARRANTY_ENVIRONMENT=production` without `WARRANTY_API_KEY` → **startup fails**
- [ ] LAN bind + key set → protected routes require `X-API-Key`; `/health` still public
- [ ] `GET /` redirects to `/docs`
- [ ] CORS only when `WARRANTY_CORS_ORIGINS` is set
- [ ] All existing tests pass; new tests cover matrix above
- [ ] `DEV-LAN-ACCESS.md` updated with required env for LAN

---

## LAN operator checklist (post-P0)

```bash
# .env
WARRANTY_ENVIRONMENT=development
WARRANTY_API_HOST=0.0.0.0
WARRANTY_API_PORT=8080
WARRANTY_API_KEY=<generate-with-openssl-rand-hex-32>
# WARRANTY_CORS_ORIGINS=http://192.168.1.100:3000

cd /path/to/quality-systems-AI/warranty
uv run warranty-api
```

Windows portproxy + firewall unchanged — see [DEV-LAN-ACCESS.md](./DEV-LAN-ACCESS.md).

Remote curl:

```bash
curl -H "X-API-Key: <key>" http://192.168.x.x:8080/adjudicate/dry-run \
  -H "Content-Type: application/json" \
  -d '{"scenario":"auto_approve"}'
```

---

## Risks / decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Fail at startup vs runtime for misconfig | **Startup** (`SystemExit`) | Fail fast; avoids silent open LAN |
| Keep `/docs` public when key required | **Yes** | Dev ergonomics; docs reveal no secrets |
| `create_app()` factory | **Yes** | Testable auth matrix without import cache bugs |
| Default host `127.0.0.1` not `0.0.0.0` | **Yes** | Secure default; LAN is opt-in |

---

## After P0 → P1 preview

Do not mix into this PR:

- LLM `<context>` delimiters in `personas.py`
- `temperature=0` in `llm.py`
- CI `--cov-fail-under=25`

Track in [plan.md](./plan.md).
