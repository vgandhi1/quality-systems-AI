# warranty — Implementation Plan & Compliance

**Tier:** T2 (release-ready) — dev environment only, not production payment software  
**Environment:** development only — not production-ready  
**Guardrails:** [QUALITY-SYSTEMS-GUARDRAILS.md](../QUALITY-SYSTEMS-GUARDRAILS.md) · [WARRANTY-ADJUDICATION-PATH.md](../WARRANTY-ADJUDICATION-PATH.md)  
**Governance:** [governance/standards/COMPLIANCE.md](../../governance/standards/COMPLIANCE.md)  
**Deck:** [presentation.html](./presentation.html)

---

## Status summary

| Area | Status | Notes |
|------|--------|-------|
| Package layout (`src/warranty/`) | Done | v0.2.0 |
| Pydantic schemas + validation gate | Done | `schema.py`, `validation.py` |
| Offline dry-run + `evaluate.py` | Done | Pinned `models/metrics.json` |
| CI (pytest + ruff + evaluate) | Done | Umbrella `.github/workflows/warranty-test.yml` |
| FastAPI service | Done | `/adjudicate/dry-run`, `/escalate/*` |
| QualityMind `RcaEscalation` contract | Done | Not CLaimLens `RcaHandoff` |
| SSRF-safe QualityMind client | Done | `qualitymind_client.py` |
| Policy search (keyword + Qdrant stub) | Done | `WARRANTY_POLICY_BACKEND` |
| `plan.md` | Done | This file |
| LAN / WSL access guide | Done | [DEV-LAN-ACCESS.md](./DEV-LAN-ACCESS.md) |
| Prod fail-closed API auth | Done | P0 |
| Configurable bind + CORS | Done | P0 |
| LLM prompt delimiters + temperature | Done | P1 — `08-AI-SECURITY.md` |
| CI coverage gate ≥ 25% | Done | P1 — raised to 50% in P3 |
| Test structure (unit/integration/contract) | Done | P2 |
| `LICENSE` + `presentation.html` | Done | P3 — T2 |
| Dependabot | Done | Umbrella `.github/dependabot.yml` |
| Temporal / ERP / production Qdrant | Deferred | Post analytical baseline |

---

## Governance compliance checklist

Reference: `governance/standards/`

### T1 — Dev

| # | Requirement | Doc | Status |
|---|-------------|-----|--------|
| 1 | `.env.example` with grouped vars | 01-ENV-VARIABLES | Done |
| 2 | `.env` gitignored; no secrets in git | 01-ENV-VARIABLES | Done |
| 3 | `README.md` with install/test/run | 04-README | Done |
| 4 | `plan.md` with status | 05-PLANNING | Done |
| 5 | `.gitignore`, CI, lockfile | 06-REQUIRED-FILES | Done (`uv.lock`) |
| 6 | Security: path sandbox, SSRF client | 07-SECURITY | Done |
| 7 | AI: output validation, agent max steps | 08-AI-SECURITY | Done |
| 8 | Offline tests + eval harness | 09-TESTING | Done (70 tests) |
| 9 | Coverage gate ≥ 25% in CI | 06-REQUIRED-FILES | Done |
| 10 | Prod fail-closed when `ENVIRONMENT=production` | 07-SECURITY | Done |

### T2 — Release-ready (current)

| Item | Status |
|------|--------|
| `LICENSE` (MIT) | Done |
| `presentation.html` + Pages workflow | Done |
| Coverage gate ≥ 50% | Done (~77%) |
| Contract tests (`RcaEscalation` ↔ QualityMind) | Done |
| Dependabot | Done |

### T3 — Production (deferred)

Tracked here; not in scope for POC:

- Rate limiting on public endpoints  
- `pip-audit` in CI  
- HTTPS reverse proxy  
- Human-in-loop before ERP `AUTO_APPROVE`  
- OPIK / full LLM observability  
- Real Qdrant cluster (replace keyword stub)

---

## Improvement backlog (prioritized)

### P0 — Before LAN / shared-network API access

1. ~~**Fail-closed auth in production**~~ — Done  
2. ~~**Configurable bind**~~ — Done (`WARRANTY_API_HOST`, `WARRANTY_API_PORT`)  
3. ~~**Require `WARRANTY_API_KEY` on non-localhost bind**~~ — Done (startup validation)  
4. ~~**CORS allowlist**~~ — Done (`WARRANTY_CORS_ORIGINS`)

### P1 — AI security (`08-AI-SECURITY.md`)

1. ~~Wrap claim/diagnostic text in `<context>` delimiters in system prompts.~~ — Done  
2. ~~Set `temperature=0` on Anthropic tool-loop calls.~~ — Done  
3. ~~Add per-call LLM timeout (30s default).~~ — Done  
4. ~~Document `MAX_CONTEXT_TOKENS` / `MAX_COMPLETION_TOKENS` in `.env.example`.~~ — Done  
5. ~~Add `tests/integration/test_tool_loop_mocked.py` (no live LLM in CI).~~ — Done  
6. ~~CI coverage gate `--cov-fail-under=25`.~~ — Done

### P2 — Test structure (`09-TESTING.md`)

```
tests/
├── unit/           # validation, routing, policy_search, handoff
├── integration/    # API TestClient, orchestrator dry-run
├── contract/       # RcaEscalation schema vs QualityMind consumer
└── conftest.py
```

**Status:** Done

### P3 — T2 public release

1. ~~Add `LICENSE`~~ — Done (MIT)  
2. ~~Add `presentation.html`~~ — Done  
3. ~~Enable Dependabot on dependency updates~~ — Done  
4. ~~Raise CI coverage to 50%~~ — Done

---

## LLM configuration (documented)

| Use case | Temperature | Model (dev default) |
|----------|-------------|---------------------|
| Agent tool loops (intake/policy/fraud/adjudicator) | **0.0** (target) | `AGENTFORGE_MODEL` / Ollama |
| Narrative-only (none in POC) | ≤ 0.4 | — |

**Agent loop limits (enforced):**

- `MAX_TOOL_STEPS = 12` per agent (`orchestrator.py`)
- Authoritative routing via `route_claim()` after LLM adjudicator

---

## Routing thresholds (pinned — do not change without re-eval)

| Constant | Value | Effect |
|----------|-------|--------|
| `AUTO_APPROVE_COST_LIMIT` | $1,500 | Above → `HUMAN_REVIEW` |
| `AUTO_APPROVE_FRAUD_MAX` | 30 | Below + covered + cost → `AUTO_APPROVE` |
| `HUMAN_REVIEW_FRAUD_MIN` | 70 | At or above → `HUMAN_REVIEW` |

Re-run `python evaluate.py` after any threshold change.

---

## Roadmap (from doc.md)

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1 | Tool sandbox + dry-run | Done |
| 2 | Personas + tool schemas | Done |
| 3 | Orchestrator + routing | Done |
| 4 | Missing-docs pause/resume | Done |
| 5 | Package + API + handoff | Done |
| 6 | Multimodal intake (video/PDF) | Open |
| 7 | Temporal workflow | Open |
| 8 | Qdrant RAG (production) | Stub only |
| 9 | ERP hook | Open |
| 10 | AgentForge preset | Open |

---

## Related docs

| File | Purpose |
|------|---------|
| [README.md](./README.md) | Install, test, run |
| [presentation.html](./presentation.html) | Visual architecture deck |
| [DEV-LAN-ACCESS.md](./DEV-LAN-ACCESS.md) | WSL2 → remote PC on same LAN |
| [doc.md](./doc.md) | Architecture deep-dive |
| [../WARRANTY-ADJUDICATION-PATH.md](../WARRANTY-ADJUDICATION-PATH.md) | Portfolio boundaries |
