# Quality Feedback — Recommendations

**Reviewer lens:** Principal Software & AI Engineer  
**Scope:** [QualityMind-RAG](QualityMind-RAG/) · [AutoClaim-VLM](AutoClaim-VLM/) · [CLaimLens](CLaimLens/)  
**Current phase:** **Dev environment — analytical models only**  
**Production:** Deferred (planned next phase)  
**Last updated:** 2026-06-06 (this chat)

> **Workflow design (text path):** [TEXT-NARRATIVE-PATH.md](TEXT-NARRATIVE-PATH.md) — how CLaimLens + QualityMind handle multi-claim warranty batches for plant/engineering insight.  
> **Guardrails:** [QUALITY-ENGG-GUARDRAILS.md](QUALITY-ENGG-GUARDRAILS.md)

---

## Change Log

Tracks all work from this review chat: initial audit → implementation → principal recommendations → dev-analytical focus.  
**Status key:** ✅ done (committed) · 🔄 done (uncommitted, local) · ⏳ recommended, not yet done

### `quality-feedback.md` (this file)

| Date | Revision |
|------|----------|
| 2026-06-06 | **v1** — Initial portfolio review (executive summary, per-project findings, cross-cutting themes, verification log) |
| 2026-06-06 | **v2** — Post-implementation review after first code pass (file lists, test counts, security score updates) |
| 2026-06-06 | **v3** — Principal recommendations only (P0–P3 by theme; production items listed) |
| 2026-06-06 | **v4** — Dev-only scope agreement; production deferred; dev sequencing + exit criteria |
| 2026-06-06 | **v5** — full change log added; reconciled with git commits + working tree |
| 2026-06-06 | **v6** — **This version** — dev-analytical WIP committed + pushed to GitHub; evaluate.py crash fixes folded in |

**Status key:** ✅ done (committed) · ☁️ pushed to GitHub origin · 🔄 done (uncommitted, local) · ⏳ recommended, not yet done

All review-chat work is now committed **and pushed** to `origin` on the default branch of each repo (QualityMind-RAG → `master`; CLaimLens, AutoClaim-VLM → `main`). Working trees clean; 0 ahead / 0 behind.

---

### QualityMind-RAG

#### ✅ Committed + ☁️ pushed (review chat)

| Commit | Summary | Key files |
|--------|---------|-----------|
| `f28137a` | SQL guard on all execution paths; upload sanitization; eval dataset path fix | `sql_service.py`, `main.py`, `evaluate.py` |
| `3c3748c` | Optional API auth; generic client errors; `STORAGE_BACKEND` default → `local`; blocking CI lint; coverage gate; auth + sanitize tests | `auth.py`, `config.py`, `utils.py`, `main.py`, `test.yml`, `tests/test_auth.py`, `tests/test_sanitize_filename.py` |
| `4a03a00` | Review bugfixes: concurrency, timeouts, lifespan, robustness | `main.py`, `auth.py`, services layer |
| `c5b1021` | Dev `structure_check` on agent routes when `ENVIRONMENT=development`; `METADATA_TEXT_MAX=3500` + `doc_id` in vector metadata | `app/api/quality_routes.py`, `app/config.py`, `app/services/vector_service.py` |

#### ⏳ Still recommended (dev)

- RAGAS eval baseline run; retrieval score threshold logging; PFMEA `doc_type` filter; HYBRID synthesis; per-route eval breakdown

#### ⏳ Still recommended (production — deferred)

- Fail-closed auth in prod; rate limits; API Gateway vs Lambda timeout; deploy gated on CI; read-only SQL role; LangGraph SQL HITL fix

**Tests (last run):** 91 passed · ~19% coverage

---

### AutoClaim-VLM

#### ✅ Committed + ☁️ pushed (review chat)

| Commit | Summary | Key files |
|--------|---------|-----------|
| `ff177ac` | Deferred AWS/GPU roadmap section in README | `README.md` |
| `50c0abb` | `total_loss_risk → ROUTE_TO_ADJUSTER`; pHash dedup in consolidation; README implementation status table; CI ruff + coverage fix | `vlm_gate.py`, `opensource_consolidation.py`, `test_vlm_gate.py`, `test.yml` |
| `28958f9` | Review bugfixes: safe zip streaming, manifest split, IaC SSE, schema tweaks | `cardd_downloader.py`, `sagemaker_manifest.py`, `infrastructure/main.tf`, `test_bugfixes.py` |
| `325b566` | Dev inference stub routes through `route_vlm_output()`; offline routing eval harness + fixtures + contract test | `src/sagemaker/inference.py`, `evaluate_routing.py`, `tests/fixtures/routing_cases.json`, `tests/fixtures/sample_vlm_output.json`, `models/routing_eval.json`, `tests/unit/test_inference_contract.py` |

#### ⏳ Still recommended (dev)

- Stratified manifest split; CRITICAL severity routing; zone vocabulary unification; dev LoRA smoke fine-tune on sample images

#### ⏳ Still recommended (production — deferred)

- End-to-end orchestration (SQS → Glue → SageMaker → warehouse); real PaliGemma fine-tune; Terraform full stack; observability/DLQ

**Tests (last run):** 25 passed · ~31% coverage

---

### CLaimLens

#### ✅ Committed + ☁️ pushed (review chat)

| Commit | Summary | Key files |
|--------|---------|-----------|
| `d3b4a39` | Fix misleading “calibrated” classifier docstring | `claimlens/classify.py` |
| `ad2fd8d` | Env config module; QualityMind handoff client; `POST /handoff/execute`; optional API auth; expanded API tests; CI coverage gate | `config.py`, `qualitymind_client.py`, `api.py`, `schema.py`, `tests/test_api.py`, `tests/test_qualitymind_client.py` |
| `224a49e` | Review bugfixes: SSRF guards, extraction/part_number, batch trends, 5-fold CV in evaluate, bugfix tests | `qualitymind_client.py`, `extract.py`, `pipeline.py`, `trends.py`, `evaluate.py`, `tests/test_bugfixes.py` |
| `4f515c3` | `needs_review` flag (confidence < 0.55); training `manifest.json` via config paths; **fix evaluate.py NameErrors** (`MODEL_OUT` removed; `macro`/`cv` used before assignment) | `claimlens/classify.py`, `claimlens/schema.py`, `claimlens/config.py`, `evaluate.py` |

#### ⏳ Still recommended (dev)

- Extraction gold eval set; confusion matrix artifact; real pilot labels (200+); DistilBERT experiment branch

#### ⏳ Still recommended (production — deferred)

- Fail-closed auth in prod; batch/payload caps; rate limiting; ~~Dockerfile + pre-baked model~~ ✅ (Dockerfile + .dockerignore; build-time train, model baked, `/health` + `/classify` verified); structured logging/metrics

**Tests (last run):** 28 passed · ~90% coverage

---

### Portfolio integration (this chat)

| Item | Status | Notes |
|------|--------|-------|
| CLaimLens → QualityMind handoff contract | ✅ | `handoff.py` payload defined |
| Live HTTP handoff (`/handoff/execute`) | ✅ committed | `qualitymind_client.py` → `/quality/five-why` |
| Full handoff context in POST body | ✅ | `problem_statement` + **`component`** (descriptive) + `anomaly_label` + `claim_count`; `component` threaded into 5-Why RAG/SQL retrieval |
| `/quality/draft-8d` execute | ✅ | `execute_handoff` drives all `target_endpoints`; per-endpoint result map; partial-failure safe |
| End-to-end localhost demo | ⏳ | Documented; requires both services running |

---

## Scope Agreement

All three repos are **not production-ready**. Work should focus on getting **analytical models runnable and measurable in dev** — train, evaluate, iterate, and demo the quality-intelligence loop locally. Production hardening is **explicitly out of scope until analytical baselines are proven**.

**Dev “analytical model ready” means:**

| Project | Dev-ready when… | Progress |
|---------|-----------------|----------|
| **CLaimLens** | `evaluate.py` → metrics + manifest; classifier serves locally; handoff → QualityMind on localhost | ☁️ manifest + `needs_review` + handoff client pushed |
| **QualityMind-RAG** | RAGAS/agent eval on golden set; fuller chunk context; dev `structure_check` on agents | ☁️ `structure_check` + wider chunk metadata pushed; ⏳ RAGAS baseline |
| **AutoClaim-VLM** | Routing eval on fixtures; inference stub through `route_vlm_output`; dev fine-tune path | ☁️ routing eval + inference gate pushed; ⏳ LoRA smoke fine-tune |

---

## Dev Environment — Do Now

### Portfolio (cross-cutting)

| Priority | Recommendation | Status |
|----------|----------------|--------|
| **D0** | Run all three locally with `ENVIRONMENT=development`; no `API_KEY` in dev | ⏳ |
| **D0** | Pin analytical artifacts (`metrics.json`, `manifest.json`, `routing_eval.json`) | 🔄 CLaimLens manifest + AutoClaim routing eval local |
| **D1** | End-to-end localhost demo: CLaimLens `/handoff/execute` → QualityMind `/quality/five-why` | ⏳ |
| **D1** | Document dev-only env vars per repo (`.env.example`) | ⏳ |

---

### CLaimLens — Dev analytical model

| Priority | Recommendation | Status |
|----------|----------------|--------|
| **D0** | `generate_sample_data.py` + `evaluate.py` before API work | ✅ script exists |
| **D0** | Model manifest alongside `.joblib` | 🔄 uncommitted |
| **D0** | `needs_review` when confidence < threshold | 🔄 uncommitted |
| **D1** | Confusion matrix + overcycle recall artifact | ⏳ |
| **D1** | Extraction gold eval (20–30 rows) | ⏳ |
| **D2** | Real pilot labels (200+) | ⏳ |
| **D2** | DistilBERT experiment branch | ⏳ |

**Dev commands:**
```bash
cd CLaimLens
python data/generate_sample_data.py
python evaluate.py
uvicorn claimlens.api:app --reload --port 8001
export QUALITYMIND_BASE_URL=http://localhost:8000
# POST /handoff/execute with sample narratives
```

---

### QualityMind-RAG — Dev analytical model

| Priority | Recommendation | Status |
|----------|----------------|--------|
| **D0** | Fix chunk context truncation (3,500 chars in metadata; cache hydration TBD) | 🔄 partial, uncommitted |
| **D0** | `structure_check` on agent endpoints in dev | 🔄 uncommitted |
| **D0** | RAGAS eval on golden set after prompt/model changes | 🔄 harness ready: `evaluate.py` pins `metrics.json` (faithfulness/relevancy + per-route + agent validation), `--check` threshold gate, offline-tested helpers (`eval_metrics.py`); **baseline numbers pending OPENAI/PINECONE/DATABASE keys + seeded docs/DB** |
| **D1** | Retrieval score threshold logging in dev | ⏳ |
| **D1** | PFMEA search `doc_type=pfmea` filter | ⏳ |
| **D1** | HYBRID synthesis (fuse SQL + RAG) | ⏳ |
| **D2** | Per-route eval breakdown in `evaluate.py` | ⏳ |
| **D2** | docker-compose as default dev path | ⏳ |

**Dev commands:**
```bash
cd QualityMind-RAG
cp .env.example .env
docker compose up -d
uvicorn app.main:app --reload --port 8000
python evaluate.py
```

---

### AutoClaim-VLM — Dev analytical model

| Priority | Recommendation | Status |
|----------|----------------|--------|
| **D0** | `evaluate_routing.py` on fixture corpus | 🔄 uncommitted |
| **D0** | Inference stub → `route_vlm_output()` | 🔄 uncommitted |
| **D0** | Stratified manifest split | ⏳ |
| **D1** | Dev LoRA smoke fine-tune (100–500 images) | ⏳ |
| **D1** | CRITICAL severity in routing matrix | ⏳ |
| **D1** | Unify zone vocabulary (CarDD vs canonical) | ⏳ |
| **D2** | Local consolidation smoke (no AWS) | ⏳ |

**Dev commands:**
```bash
cd AutoClaim-VLM
PYTHONPATH=src pytest tests/unit -q
PYTHONPATH=src python evaluate_routing.py
python -m claimlens.vlm_gate --input tests/fixtures/sample_vlm_output.json
```

---

## Production — Deferred (When Analytical Baselines Are Proven)

Do not prioritize while dev analytical work is in flight.

### Security & access
- Fail-closed auth in production · Rate limiting · SQL HITL everywhere (incl. LangGraph) · Read-only DB role · KMS/IAM/Secrets Manager

### Infrastructure & deploy
- API Gateway vs Lambda timeout · Full Terraform + remote state · Deploy gated on CI · Containerized CLaimLens

### Observability & ops
- Structured logging + correlation IDs · Prometheus/CloudWatch · DLQ/alarms · Model registry · Great Expectations

### Model production SLAs
- Real labeled data · Confidence calibration (ECE) · Load/soak testing · Full PaliGemma fine-tune (~160K)

---

## Recommended Dev Sequencing (4–6 weeks)

```text
Week 1   ✅/🔄 CLaimLens evaluate + manifest + needs_review (local)
         ✅/🔄 QualityMind chunk truncation + structure_check (local)
         ✅/🔄 AutoClaim evaluate_routing + inference→gate (local)
         → Commit uncommitted dev-analytical changes

Week 2   End-to-end localhost demo (CLaimLens → QualityMind)
         QualityMind: RAGAS baseline + retrieval threshold logging
         AutoClaim: stratified manifest + CRITICAL routing

Week 3   CLaimLens: extraction gold eval
         QualityMind: PFMEA filter + hybrid synthesis prototype
         AutoClaim: zone vocabulary + local consolidation smoke

Week 4   CLaimLens: pilot label collection starts
         AutoClaim: dev LoRA smoke fine-tune
         All: lock analytical baselines in model artifacts

Week 5–6 Buffer: close dev exit criteria; prep production backlog
```

---

## Analytical Success Criteria (Dev Exit Gate)

| Project | Criteria | Current |
|---------|----------|---------|
| **CLaimLens** | Holdout + 5-fold CV documented; `needs_review`; local handoff demo | 🔄 CV in metrics; manifest local; handoff client ✅ |
| **QualityMind-RAG** | RAGAS threshold met; `structure_check` tracked; full chunk context | 🔄 partial truncation + structure_check local |
| **AutoClaim-VLM** | 100% routing eval on fixtures; inference through gate; LoRA smoke done | 🔄 routing eval local; ⏳ LoRA |

---

## Summary

**Not production-ready** — by agreement. This chat produced: initial review → committed hardening across all three repos → dev-analytical additions (partially uncommitted). **`quality-feedback.md` is now aligned with that history via the Change Log above.**

**Next doc-only action:** none required until the next review pass.  
**Next code action (when ready):** commit uncommitted dev-analytical changes, then Week 2 items (RAGAS baseline, localhost E2E demo).
