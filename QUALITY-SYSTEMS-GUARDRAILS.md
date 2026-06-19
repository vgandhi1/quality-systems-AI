# Quality Systems Portfolio — AI Guardrails
# Covers: QualityMind-RAG · CLaimLens · AutoClaim-VLM · automotive-visual-qa-engine
# Last updated: 2026-06-19

> **Inherits the workspace safety baseline:** [`../governance/Guardrails/core/safety-baseline.md`](../governance/Guardrails/core/safety-baseline.md).
> That file is the single source of truth for cross-project safety (read-only by default,
> irreversible-action confirmation, secrets/PII redaction, no-guessing on coded data, grounding, scope).
> Rules in this document **tighten** the baseline for the quality domain — they never loosen it.
> If a rule here conflicts with the baseline, the stricter one wins.

---

## Portfolio ecosystem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         QUALITY SYSTEMS PORTFOLIO                           │
├──────────────────────────────┬──────────────────────────────────────────────┤
│  TEXT / NARRATIVE PATH       │  VISION PATH                                 │
│                              │                                              │
│  CLaimLens                   │  automotive-visual-qa-engine                 │
│  (warranty narratives)       │  (line-side trim / surface inspection)       │
│       │                      │       │ edge CLIP → cloud VLM → rework bay     │
│       │ /handoff             │       │                                      │
│       ▼                      │  AutoClaim-VLM                               │
│  QualityMind-RAG             │  (insurance / fleet damage photos)           │
│  (RAG + Text-to-SQL +        │       │ VLM → confidence routing → adjuster  │
│   LangGraph RCA agents)      │                                              │
└──────────────────────────────┴──────────────────────────────────────────────┘
```

**Naming note:** AutoClaim-VLM contains an internal Python package named `claimlens` (`src/claimlens/`). That is **not** the CLaimLens narrative-NLP repo. Do not merge, rename, or cross-import between them without an explicit integration decision.

---

## Project scope map

| Concern | QualityMind-RAG | CLaimLens | AutoClaim-VLM | automotive-visual-qa-engine | Neither / all |
|---|---|---|---|---|---|
| RAG over PFMEA / CAPA / 8D / QMS docs | ✅ | ❌ | ❌ | ❌ | — |
| Text-to-SQL against quality DB | ✅ | ❌ | ❌ | ❌ | — |
| 5-Why / Fishbone / CAPA / 8D LangGraph agents | ✅ | ❌ | ❌ | ❌ | — |
| Warranty / field narrative NLP extraction | ❌ | ✅ | ❌ | ❌ | — |
| Overcycle anomaly classification | ❌ | ✅ | ❌ | ❌ | — |
| Pareto failure trend aggregation | ❌ | ✅ | ❌ | ❌ | — |
| CLaimLens → QualityMind handoff payload | ❌ | ✅ | ❌ | ❌ | — |
| Vehicle damage image VLM (insurance / fleet) | ❌ | ❌ | ✅ | ❌ | — |
| Confidence-based claims routing (adjuster / repair) | ❌ | ❌ | ✅ | ❌ | — |
| AWS Glue / Redshift ETL for damage claims | ❌ | ❌ | ✅ | ❌ | — |
| Edge CLIP pass–fail inspection (Jetson) | ❌ | ❌ | ❌ | ✅ | — |
| Manufacturing rework routing (SAP / MES mock) | ❌ | ❌ | ❌ | ✅ | — |
| IoT MQTT + Step Functions orchestration | ❌ | ❌ | ❌ | ✅ | — |
| ML model training pipelines | ❌ | ❌ | Stub only — offline eval first | ❌ | Skip — use existing trained models |
| ERP / MES / SAP live integration | ❌ | ❌ | ❌ | ❌ | Skip — demo scope only |
| PII in any dataset or output | ❌ | ❌ | ❌ | ❌ | Hard no |
| Real customer warranty / claim records | ❌ | ❌ | ❌ | ❌ | Hard no — synthetic only |

**Companion relationship (text path):** CLaimLens is the narrative→signal front end. QualityMind-RAG is the signal→corrective-action back end. They communicate via the `/handoff` endpoint. Do not duplicate RCA logic in CLaimLens.

**Workflow design (text path):** See [TEXT-NARRATIVE-PATH.md](TEXT-NARRATIVE-PATH.md) — multi-claim warranty intake, Pareto review, and plant/engineering insight loop.

**Vision paths are independent:** AutoClaim-VLM (post-incident damage assessment) and automotive-visual-qa-engine (in-line manufacturing inspection) share VLM patterns but serve different domains. Do not share schemas, routing tables, or model artifacts between them without a documented contract.

---

## Part 1 — QualityMind-RAG AI Guardrails

### SQL safety guardrails (hard rules — no exceptions)

| Guardrail | Rule |
|---|---|
| Dangerous pattern block | `DROP`, `DELETE`, `TRUNCATE`, `ALTER` always blocked by `check_dangerous_sql()` in `app/utils.py` before any execution |
| Human-in-the-loop | SQL returned for human review before execution. `auto_approve_sql=true` is for testing only — never set it in production or agent-generated SQL paths |
| No raw LLM SQL execution | LLM outputs query intent; Vanna + PostgreSQL layer owns actual SQL construction |
| Schema append-only | `data/sql/schema.sql` is the source of truth. Never edit existing tables — add new columns via ALTER only if explicitly confirmed |
| Parameterized queries only | All direct PostgreSQL calls in `quality_data_service.py` use parameterized queries — no f-strings in SQL |

### RAG output guardrails

| Guardrail | Rule |
|---|---|
| Grounded citations required | Every answer must cite the source document chunk (heading breadcrumb format: `PFMEA > Station 12 > Torque Verification`) |
| No answer from weights alone | Always retrieve before answering — never let the LLM answer from training knowledge for operational data |
| Temperature discipline | 0.0 for SQL generation (Vanna), 0.0 for structured JSON agents, 0.4 for narrative (SPC summaries) |
| Empty retrieval handling | If Pinecone returns zero results, return a structured "no context found" response — never hallucinate a plausible answer |
| RAGAS thresholds | Faithfulness > 0.75, Answer Relevancy > 0.80 — run `evaluate.py` before marking any RAG change as complete |

### LangGraph agent guardrails

| Guardrail | Rule |
|---|---|
| Output schema enforcement | All agent outputs validated against `app/agent_validation.py` before returning to caller |
| 5-Why: minimum 3 levels | `whys` list must have ≥ 3 entries — reject and re-prompt if fewer returned |
| 5-Why: confidence in range | `confidence_score` must be 0.0–1.0 — reject if out of range |
| Fishbone: all 6M bones | All of Man / Machine / Method / Material / Measurement / Environment must be present and non-empty |
| CAPA: 4 required fields | `problem_statement`, `root_cause`, `corrective_action`, `preventive_action` must all be present |
| 8D: all D1–D8 populated | All disciplines must have content — partial 8D drafts are not valid output |
| Evidence citation required | Every cause / why level must have an `evidence_source` field — empty evidence is a failed output |
| Agent SQL auto-execution | Agent-generated SQL (in workflows) is blocked by `check_dangerous_sql()` — this is the safety compensator for the lack of human review in agent paths |
| Max RAG + SQL calls per agent | Enforce the existing LangGraph graph limits — do not add unbounded tool-call loops |

### Caching + observability rules

| Rule | Detail |
|---|---|
| Never cache write-side | Redis query cache is for SELECT results only — never cache mutation operations |
| OPIK tracing on all agent endpoints | Every `/quality/*` endpoint must have OPIK trace context — don't add endpoints without wiring tracing |
| Redis degradation | App must serve requests without Redis — cache miss is acceptable, cache hard failure is not a crash |
| Document cache | SHA-256 deduplication skips re-embedding identical files — don't bypass this check when adding new upload paths |

---

## Part 2 — CLaimLens AI Guardrails

### Classifier guardrails

| Guardrail | Rule |
|---|---|
| Confidence threshold | Low-confidence predictions must be flagged — `needs_review=true` when confidence < 0.55; never auto-accept without a confidence score |
| No PII in corpus | `generate_sample_data.py` produces synthetic labels only — no real vehicle IDs, operator names, or customer data |
| Model file is generated | `models/anomaly_clf.joblib` is a build artifact — never commit it to the repo; regenerate with `evaluate.py` |
| Deterministic train/test split | `generate_sample_data.py` uses a fixed seed — do not change the seed without updating the expected F1 scores in tests |
| F1 regression check | If a code change drops macro F1 below 0.88, it's a regression — investigate before merging |
| Taxonomy is locked | The 5 labels (`soft_reset`, `cloud_sync`, `power_cycle`, `connectivity_loss`, `no_fault`) are the ground truth taxonomy. Do not add or rename labels without updating `schema.py`, tests, and `evaluate.py` together |

### Extraction guardrails

| Guardrail | Rule |
|---|---|
| Regex-first, LLM-last | `extract.py` uses rule-based extraction (regex + gazetteers) — do not replace with LLM extraction without explicit decision |
| Part number patterns | Part number regex must not match PII patterns — test with edge cases |
| No external calls in extract | `extract.py` is offline-only — keep it free of API calls |

### Handoff contract guardrails

The `/handoff` endpoint produces the bridge payload to QualityMind-RAG. This output schema is a **cross-project contract**:

```python
# Required fields — never remove or rename without updating QualityMind's consumer
{
    "problem_statement": str,   # QualityMind /quality/five-why and /quality/draft-8d consume this
    "component": str,           # descriptive name from extraction/trends (e.g. "Telematics Control Unit")
    "anomaly_label": str,       # must be one of the 5 taxonomy labels
    "target_endpoints": list    # which QualityMind endpoints to invoke
}
```

**Not in handoff:** Customer complaints use **`component` names only**. BOM / part-number identifiers belong to QualityMind engineering routes (`/quality/ncr-history`, `/quality/spc-summary`) and the quality DB — not the CLaimLens API or `RcaHandoff`.

Any change to this schema requires updating both CLaimLens and QualityMind-RAG simultaneously.

### QualityMind client guardrails

| Guardrail | Rule |
|---|---|
| SSRF prevention | `qualitymind_client.py` validates `QUALITYMIND_BASE_URL` against an allowlist — do not bypass with raw user-supplied URLs |
| Fail-safe handoff | `/handoff/execute` must handle QualityMind unavailability gracefully — return structured error, not raw exception text |
| Auth in production | Optional `API_KEY` in dev; fail-closed auth required before any production deployment |

---

## Part 3 — AutoClaim-VLM AI Guardrails

AutoClaim-VLM is the insurance / fleet **damage-image** pipeline. Internal package: `src/claimlens/` (VLM gate + image QA). Do not confuse with the CLaimLens narrative repo.

### VLM output + routing guardrails

| Guardrail | Rule |
|---|---|
| Schema-first gate | All VLM outputs must pass `validate_vlm_output()` in `src/claimlens/vlm_gate.py` (JSON Schema draft-07, `src/schema/vlm_output_schema.json`) before routing or any downstream write |
| Single routing entrypoint | Call `route_vlm_output()` — never duplicate routing logic elsewhere. SageMaker inference stub must route through this gate |
| Confidence tiers (locked) | ≥ 0.90 + MINOR/COSMETIC → `AUTO_APPROVE`; ≥ 0.75 + MODERATE/MAJOR → `QUEUE_FOR_REPAIR`; ≥ 0.60 → `FLAG_REVIEW`; else → `ROUTE_TO_ADJUSTER` |
| Total-loss override | `total_loss_risk=true` always routes to `ROUTE_TO_ADJUSTER` regardless of confidence — do not remove this override |
| Invalid output handling | Schema failures must be caught and escalated — never silently write invalid VLM JSON to S3 / Redshift / DynamoDB |
| Severity enum locked | `CRITICAL`, `MAJOR`, `MODERATE`, `MINOR`, `COSMETIC` — changes require schema + tests + `evaluate_routing.py` fixtures together |
| Offline routing eval | Run `PYTHONPATH=src python evaluate_routing.py` before merging routing or schema changes; pin results in `models/routing_eval.json` |

### Image ingest + data quality guardrails

| Guardrail | Rule |
|---|---|
| Quality gates before VLM | `passes_quality_gates()` in `src/opensourceingest/image_quality.py` enforces min resolution and blur score — reject blurry / undersized images upstream |
| Standardized resize | Pipeline output is 640×640 JPEG — do not change dimensions without updating SageMaker input contract and tests |
| pHash deduplication | Perceptual-hash dedup in consolidation prevents duplicate training / inference records — do not bypass in new ingest paths |
| Safe archive extraction | Zip/tar members validated via `pathutil.is_safe_zip_member()` and `ensure_within_directory()` — no path traversal in dataset downloaders |
| Open-source training only | CompCars, CarDD, Kaggle, HuggingFace datasets are for **model training** under academic licenses — do not redistribute; production inference uses operational claims images only |
| No real PII in fixtures | Test images and VLM fixture JSON must use synthetic / open-source samples — no real VINs, policy numbers, or customer photos in repo |

### AWS / infrastructure guardrails (dev phase)

| Guardrail | Rule |
|---|---|
| Stubs stay offline-testable | SageMaker train/inference, Glue Spark jobs, and Lambda enrichment are stubs until GPU/AWS available — unit tests must pass without credentials |
| Integration tests gated | `@pytest.mark.dev` integration tests skip in CI — require `AWS_INTEGRATION=1` and deployed dev environment |
| Terraform scope | `infrastructure/main.tf` is partial (S3 today) — do not apply undeclared modules to production without review |
| Model artifacts not committed | Fine-tuned weights, `.joblib`, and large dataset shards stay out of git — S3 / local build only |
| Secrets via env / Secrets Manager | Kaggle tokens, GDrive tokens, AWS keys — never hardcode; use `.env.example` as template |

---

## Part 4 — automotive-visual-qa-engine AI Guardrails

Manufacturing **line-side visual QA**: edge CLIP on Jetson → MQTT → cloud VLM escalation → rework routing (SAP mock). Independent from AutoClaim-VLM damage-assessment schema.

### Edge inference guardrails

| Guardrail | Rule |
|---|---|
| Confidence threshold (locked) | Default 0.75 in `edge/prompts.json` → `routing.confidence_threshold`. Low confidence triggers VLM escalation via `should_escalate()` — do not auto-pass ambiguous frames |
| PASS vs FAIL discipline | CLIP compares pass prompts vs defect prompts; confidence must stay in 0.0–1.0 — test with `edge/tests/test_inference.py` |
| Prompt changes are model changes | Updating zero-shot prompts in `prompts.json` requires re-benchmarking — treat prompt edits like hyperparameter changes |
| Synthetic dev mode | `python main.py --synthetic --mqtt-offline-only` is the offline dev path — no camera or AWS required for local iteration |
| Offline buffer integrity | SQLite queue in `offline_buffer.py` preserves MQTT messages during disconnect — do not drop messages on transient failures |
| Anomaly crop bounds | `min_crop_size_px: 500` in prompts routing config — crops below this threshold should not escalate to VLM |

### Cloud VLM + rework routing guardrails

| Guardrail | Rule |
|---|---|
| VLM output validation | `cloud/lambda/vlm_orchestrator/index.py` validates defect_type (allowlist), severity, repair_action, rework_station, and confidence range before Step Functions |
| Defect taxonomy locked | Allowed types: `scratch`, `paint_drip`, `weld_defect`, `dent`, `blister`, `overspray`, `contamination`, `unknown` — changes require lambda + MES model + integration test updates |
| Fail-safe on invalid VLM | Invalid VLM JSON routes to `_manual_review_payload()` with `confidence: 0.0` — never propagate unvalidated structured output to SAP / MES |
| Stub when no endpoint | When `VLM_ENDPOINT_NAME` is unset, stub response is used for dev — clearly marked; do not treat stub output as production metrics |
| Step Functions naming | Execution names sanitized via `_safe_execution_name()` — no raw VIN characters that break AWS naming rules |

### MES / SAP mock guardrails

| Guardrail | Rule |
|---|---|
| Pydantic at API boundary | `cloud/mes_service/models.py` defines `DefectRecord` and `InspectionResult` — never raw dicts at FastAPI endpoints |
| Synthetic VINs only | Use `TESTVIN*` / `SAMPLEVIN*` in fixtures and dev config — no real vehicle identifiers |
| No credential logging | MES service must not log full defect payloads containing VIN + image URLs to stdout in production paths |

### Security guardrails (edge + cloud)

| Guardrail | Rule |
|---|---|
| IoT certs never committed | X.509 device certificates and private keys stay in `certs/` (gitignored) — provision via `provision_iot_cert.sh` |
| Least-privilege IoT topics | Devices publish only to `vehicles/{vin}/inspection/*` — no wildcard publish policies |
| Lambda IAM minimal | Each Lambda gets only required S3 / DynamoDB / SNS / SageMaker actions — defined in `cloud/terraform/iam.tf` |

---

## Part 5 — Shared rules (all projects)

### Python conventions

| Project | Lint / format | Notes |
|---|---|---|
| QualityMind-RAG | `ruff check` + `ruff format` | Type hints on all function signatures |
| CLaimLens | `ruff check` + `ruff format` | Pydantic models for all API schemas |
| AutoClaim-VLM | `ruff check` (CI) | `pyproject.toml` pytest config |
| automotive-visual-qa-engine | No ruff in CI yet | Follow ruff if adding Python modules |

Common across all:
- Pydantic models for all API request/response schemas — never raw dicts at API boundaries
- `logging` module only — no `print()` in production code
- No mutable default arguments
- `pytest` for all tests — unit tests must run offline (no live API/DB/AWS calls in default CI)

### Security baseline

Generic rules (no `.env` commits, API keys via env only, no secrets/PII in logs, input
validation on every endpoint) come from [`safety-baseline.md`](../governance/Guardrails/core/safety-baseline.md)
§3 — not restated here. The items below are the **quality-domain tightenings** on top of it:

- SQL injection (QualityMind only): parameterized queries + `check_dangerous_sql()` as second layer
- SSRF (CLaimLens handoff client): allowlisted base URLs only
- Path traversal (AutoClaim-VLM ingest): `pathutil` guards on all archive extraction
- PII scrub specifics: narrative text, VINs, policy numbers, and image metadata stripped before CloudWatch / stdout

### Testing rules

| Project | Unit tests (approx.) | Offline eval harness |
|---|---|---|
| QualityMind-RAG | 91 | `evaluate.py` (RAGAS — separate from pytest) |
| CLaimLens | 28 | `evaluate.py` (macro F1 + manifest) |
| AutoClaim-VLM | 25 | `evaluate_routing.py` (schema + routing fixtures) |
| automotive-visual-qa-engine | 7 | `edge/main.py --synthetic`; `tests/integration_test.py` |

- New logic = new test. No exceptions.
- Agent / VLM output tests must use mocks or fixtures — never call live OpenAI / SageMaker in CI
- Analytical eval scripts (`evaluate.py`, `evaluate_routing.py`) run separately from pytest — don't merge them into unit test suites unless explicitly requested
- All unit tests in all four repos must pass before any merge

### Git / CI

- Commit format: `<type>(<scope>): <description>` — feat, fix, refactor, test, docs, chore
- Never commit: model weights, `.joblib`, `.env`, generated data CSVs, IoT certificates, `__pycache__`
- `.github/workflows/` — off-limits except with explicit intent
- GitHub Actions runs `pytest` (and `ruff` where configured) on every push — do not break CI

### Dev environment defaults

All four repos are in **dev / analytical-model phase** — not production-ready:
- `ENVIRONMENT=development` locally; no `API_KEY` required in dev where optional auth exists
- Pin analytical artifacts after eval runs: `metrics.json`, `manifest.json`, `routing_eval.json`
- Production hardening (fail-closed auth, rate limits, full Terraform, real SAP OData) is deferred until analytical baselines are proven

---

## Part 6 — Hard NOs (permanent for all projects)

1. **No real warranty / customer / claims data** — synthetic or open-source academic datasets only
2. **No PII in any file, log, or output** — names, vehicle IDs, policy numbers, operator IDs must be anonymized or synthetic
3. **No auto-executing SQL** without dangerous-pattern check (QualityMind) — `check_dangerous_sql()` is mandatory
4. **No LLM / VLM outputs rendered to users without validation** — QualityMind via `agent_validation.py`; AutoClaim-VLM via `vlm_gate.py`; visual QA via `_validate()` in vlm_orchestrator
5. **No live OpenAI / SageMaker calls in unit tests** — mock the model for all pytest runs
6. **No ML retraining pipelines in CI** — use existing trained models / stubs; flag for retraining if metrics regress
7. **No cross-project logic duplication** — CLaimLens extracts/classifies; QualityMind does RCA; AutoClaim-VLM assesses damage images; visual-qa-engine inspects manufacturing surfaces; keep boundaries clean
8. **No handoff contract changes without updating both sides** — CLaimLens `schema.py` ↔ QualityMind consumer
9. **No mixing AutoClaim-VLM and visual-qa-engine schemas** — different VLM output contracts, routing tables, and domains
10. **No committing the internal AutoClaim `claimlens` package changes into the CLaimLens repo** (or vice versa) — separate codebases

---

## Part 7 — Quality-domain AI guardrails (LLM / VLM behavior)

### QualityMind-RAG (text LLM)

```
System prompt structure for all QualityMind LLM calls:
1. Role: "You are a manufacturing quality engineering assistant..."
2. Scope: "Answer only from the retrieved context below. If insufficient context, say so."
3. Data context: <data> blocks — never inline as plain text
4. Output format: explicit JSON schema for structured endpoints
5. Grounding: "Cite the source document and section for every claim."
6. Refusal: "If the question is outside quality engineering, decline and explain."
```

**Hallucination mitigations already in place — do not remove:**
- Vanna temperature=0, seed=42 for SQL generation
- RAG retrieves before answering — model weights not used alone for operational data
- `check_dangerous_sql()` blocks mutation patterns
- `agent_validation.py` rejects structurally invalid agent outputs
- RAGAS evaluation tracks faithfulness and relevancy regression

### AutoClaim-VLM + automotive-visual-qa-engine (vision / VLM)

```
VLM output discipline (both vision projects):
1. Structured JSON only — no free-text damage / defect descriptions without schema fields
2. Confidence always present and in [0.0, 1.0]
3. Schema validation before any write or routing decision
4. Low confidence → human review path (FLAG_REVIEW / manual_review / ROUTE_TO_ADJUSTER)
5. Never infer financial estimates or rework actions without validated severity + zones
6. Refusal: if image quality gates fail, reject upstream — do not ask the VLM to classify unusable input
```

**Vision-specific mitigations — do not remove:**
- AutoClaim-VLM: `route_vlm_output()` single gate; `total_loss_risk` override; blur / resolution QA
- automotive-visual-qa-engine: edge CLIP tier saves ~85–90% of VLM cost; invalid VLM → manual review payload
- Both: offline eval harnesses (`evaluate_routing.py`, synthetic edge mode) before any GPU fine-tune

---

## Quick reference — where to look

| Guardrail type | Primary file(s) |
|---|---|
| SQL safety | QualityMind-RAG `app/utils.py`, `app/services/sql_service.py` |
| Agent output validation | QualityMind-RAG `app/agent_validation.py` |
| Narrative handoff contract | CLaimLens `claimlens/schema.py` (`RcaHandoff`) |
| Publisher→subscriber simulation | [PUBLISHER-SUBSCRIBER-SIMULATION.md](PUBLISHER-SUBSCRIBER-SIMULATION.md) |
| SSRF on handoff | CLaimLens `claimlens/qualitymind_client.py` |
| Damage VLM schema + routing | AutoClaim-VLM `src/claimlens/vlm_gate.py`, `src/schema/vlm_output_schema.json` |
| Image QA gates | AutoClaim-VLM `src/opensourceingest/image_quality.py` |
| Archive path safety | AutoClaim-VLM `src/opensourceingest/pathutil.py` |
| Edge CLIP threshold | automotive-visual-qa-engine `edge/prompts.json`, `edge/clip_inference.py` |
| Cloud VLM validation | automotive-visual-qa-engine `cloud/lambda/vlm_orchestrator/index.py` |
| MES API schemas | automotive-visual-qa-engine `cloud/mes_service/models.py` |
