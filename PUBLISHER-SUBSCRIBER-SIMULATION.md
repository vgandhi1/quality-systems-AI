# Publisher → Subscriber Simulation Guide

**Publisher:** [CLaimLens](CLaimLens/) — warranty narrative NLP, Pareto trends, RCA handoff  
**Subscriber:** [QualityMind-RAG](QualityMind-RAG/) — RAG + LangGraph agents (5-Why, 8D, …)  
**Guardrails:** [QUALITY-ENGG-GUARDRAILS.md](QUALITY-ENGG-GUARDRAILS.md)  
**Architecture context:** [TEXT-NARRATIVE-PATH.md](TEXT-NARRATIVE-PATH.md)  
**Phase:** Dev / analytical only — synthetic data, human review before action  
**Last updated:** June 2026  
**Implementation review:** June 2026 (read-only audit vs repo — see [§ Implementation review](#implementation-review-read-only))

---

## What you are simulating

This is not a message bus (Kafka/SQS). It is an **HTTP request/response handoff**:

```text
┌─────────────────────────────┐         ┌──────────────────────────────┐
│  CLaimLens  (publisher)     │  POST   │  QualityMind-RAG (subscriber)│
│  port 8001                  │ ──────► │  port 8000                   │
│                             │         │                              │
│  /trends        → Pareto    │         │  /quality/five-why           │
│  /handoff       → payload   │         │  /quality/draft-8d           │
│  /handoff/execute → both    │         │  (+ RAG / SQL behind agents) │
└─────────────────────────────┘         └──────────────────────────────┘
```

| Role | Repo | Responsibility |
|------|------|----------------|
| **Publisher** | CLaimLens | Ingest batch → extract **component** → classify → Pareto → build `RcaHandoff` |
| **Subscriber** | QualityMind-RAG | Consume handoff → run RCA agents with PFMEA/CAPA/NCR context |
| **Contract** | `RcaHandoff` in `CLaimLens/claimlens/schema.py` | Cross-repo JSON — change both sides together |

Customer complaints use **`component` names only** (e.g. `"Telematics Control Unit"`). BOM / part-number identifiers are **engineering metadata** inside QualityMind’s quality DB and `/quality/ncr-history` / `/quality/spc-summary` routes — they are **not** part of the CLaimLens API or handoff contract.

---

## Simulation modes

| Mode | How to run | QualityMind? | OpenAI cost? | Best for |
|------|------------|--------------|--------------|----------|
| **A — Analyze + Pareto** | `--mode trends` | No | No | Classifier + Pareto sanity check |
| **B — Handoff dry-run** | `--mode handoff` | No | No | Inspect `RcaHandoff` contract |
| **C — Live execute** | `--mode execute` | Yes (8000) | Yes | Full publisher→subscriber demo |
| **D — Offline report** | execute + subscriber down | No | No | CI / portfolio HTML without API keys |

**Recommendation:** Run **B** before **C**. Verify `problem_statement`, `component`, and `anomaly_label` before spending tokens.

### `ClaimNarrative` input (customer side)

POST bodies accept **free-text only** plus optional metadata:

| Field | Required | Example |
|-------|----------|---------|
| `narrative` | ✅ | `"TCU watchdog soft reset after ignition cycle"` |
| `claim_id` | optional | `"WC-1001"` |
| `source_type` | optional | `"customer_complaint"` · `"dealer_ro"` · `"field_log"` |

There is **no** `part_number` field on customer ingest. `extract.py` derives the descriptive **`component`** from narrative keywords (TCU → Telematics Control Unit, gateway → Connectivity Gateway, etc.).

### `RcaHandoff` output (cross-repo contract)

| Field | Example | Subscriber use |
|-------|---------|----------------|
| `problem_statement` | `"Recurring spontaneous reboot on Telematics Control Unit (Soft Reset) — 2 field claims, 67% …"` | Seeds 5-Why / 8D |
| `component` | `"Telematics Control Unit"` | RAG + agent context scope |
| `anomaly_label` | `"soft_reset"` | Taxonomy traceability |
| `claim_count`, `share` | `2`, `0.6667` | Severity context |
| `target_endpoints` | `["/quality/five-why", "/quality/draft-8d"]` | Driven by `execute_handoff()` |

---

## Prerequisites

### CLaimLens (publisher)

```bash
cd CLaimLens
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python data/generate_sample_data.py   # data/claims.csv (component column, no part_number)
python evaluate.py                    # models/anomaly_clf.joblib

cp .env.example .env
# For live execute:
#   QUALITYMIND_BASE_URL=http://localhost:8000

uvicorn claimlens.api:app --reload --port 8001
```

Verify: `curl -s http://localhost:8001/health | jq .` → `model_file_present: true`

### QualityMind-RAG (subscriber)

```bash
cd QualityMind-RAG
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# OPENAI_API_KEY, PINECONE_API_KEY, DATABASE_URL, ENVIRONMENT=development

docker compose up -d    # Postgres + Redis (optional)
# Seed PFMEA/CAPA docs + DB per QualityMind README for RAG citations

export ENVIRONMENT=development
uvicorn app.main:app --reload --port 8000
```

Verify: `curl -s http://localhost:8000/health | jq .`

### Optional auth (skip in dev)

| Variable | Service | Dev default |
|----------|---------|-------------|
| `CLAIMLENS_API_KEY` | CLaimLens | unset = open |
| `QUALITYMIND_API_KEY` | QualityMind | unset = open |
| `QUALITYMIND_BASE_URL` | CLaimLens client | `http://localhost:8000` |

---

## Quick start — HTML report (orchestrator)

The portfolio includes a **stdlib-only** orchestrator that drives the publisher APIs and writes a self-contained HTML report:

```bash
# From quality-engineering/ repo root — no venv required for the script itself
python scripts/simulate_text_path.py --mode handoff
# → reports/text-path-<timestamp>.html

# Live subscriber (both services must be running)
export QUALITYMIND_BASE_URL=http://localhost:8000
python scripts/simulate_text_path.py --mode execute

# Custom batch JSON (narrative + optional claim_id + source_type only)
python scripts/simulate_text_path.py --batch /tmp/claims.json --mode execute --out reports/demo.html
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--mode` | `execute` | `trends` · `handoff` · `execute` |
| `--publisher` | `http://127.0.0.1:8001` | CLaimLens base URL |
| `--subscriber` | `$QUALITYMIND_BASE_URL` or `http://127.0.0.1:8000` | QualityMind base URL |
| `--timeout` | `60` | Per-request seconds |
| `--out` | `reports/text-path-<timestamp>.html` | Output path |

**Mode D (automatic):** If `--mode execute` but subscriber `/health` fails, the script still writes HTML with a mock subscriber panel — useful without OpenAI keys.

---

## Step-by-step simulation (curl)

### Step 1 — health checks

```bash
curl -s http://localhost:8000/health | jq .
curl -s http://localhost:8001/health | jq .
```

### Step 2 — batch Pareto (publisher only)

Use narratives with **overcycle** vocabulary so `/handoff` succeeds later.

```bash
curl -s -X POST http://localhost:8001/trends \
  -H "Content-Type: application/json" \
  -d @- <<'EOF' | jq .
[
  {"narrative": "TCU watchdog soft reset after ignition cycle", "claim_id": "WC-1001"},
  {"narrative": "Gateway fails cloud sync retries exhausted overnight", "claim_id": "WC-1002"},
  {"narrative": "Soft reset again on telematics unit every morning", "claim_id": "WC-1003"},
  {"narrative": "Infotainment OTA download stalls map sync never completes", "claim_id": "WC-1004"},
  {"narrative": "No fault found bench test passed all checks", "claim_id": "WC-1005"}
]
EOF
```

**Inspect:** `by_label`, `by_component`, `overcycle_share`. If `overcycle_share` is 0, `/handoff` returns 404.

### Step 3 — handoff dry-run

```bash
curl -s -X POST http://localhost:8001/handoff \
  -H "Content-Type: application/json" \
  -d @- <<'EOF' | jq .
[
  {"narrative": "TCU watchdog soft reset after ignition cycle"},
  {"narrative": "Soft reset again on telematics unit every morning"},
  {"narrative": "Gateway fails cloud sync retries exhausted"}
]
EOF
```

Expect `"component": "Telematics Control Unit"` (or `"Connectivity Gateway"` depending on dominant trend).

### Step 4 — live publisher → subscriber

```bash
curl -s -X POST http://localhost:8001/handoff/execute \
  -H "Content-Type: application/json" \
  -d @- <<'EOF' | tee /tmp/handoff_execute.json | jq .
[
  {"narrative": "TCU watchdog soft reset after ignition cycle"},
  {"narrative": "Soft reset again on telematics unit every morning"},
  {"narrative": "Gateway fails cloud sync retries exhausted"}
]
EOF
```

**Response shape (`RcaHandoffResponse`):**

```json
{
  "problem_statement": "...",
  "component": "Telematics Control Unit",
  "anomaly_label": "soft_reset",
  "claim_count": 2,
  "share": 0.6667,
  "target_endpoints": ["/quality/five-why", "/quality/draft-8d"],
  "qualitymind_response": {
    "/quality/five-why": {
      "status": "ok",
      "response": {
        "status": "success",
        "analysis": { "whys": [...], "confidence_score": 0.82 },
        "structure_check": { "valid": true, "errors": [] }
      }
    }
  }
}
```

Partial failure: per-endpoint `ok` / `error` / `skipped`; HTTP 502 only when **all** endpoints fail.

### Step 5 — direct subscriber call (isolation test)

```bash
curl -s -X POST http://localhost:8000/quality/five-why \
  -H "Content-Type: application/json" \
  -d '{
    "problem_statement": "Recurring cloud sync failure on gateway module — 12 field claims",
    "component": "Connectivity Gateway",
    "anomaly_label": "cloud_sync",
    "claim_count": 12
  }' | jq .
```

---

## Using the dev CSV corpus

`CLaimLens/data/claims.csv` columns (after regenerating): `claim_id`, `date`, `vin`, **`component`**, `narrative`, `label`. The generator script no longer writes a `part_number` column — **regenerate** if your local CSV still has the old header:

```bash
cd CLaimLens && python data/generate_sample_data.py
```

```bash
cd CLaimLens
python - <<'PY'
import csv, json
rows = []
with open("data/claims.csv") as f:
    for i, row in enumerate(csv.DictReader(f)):
        if i >= 25:
            break
        rows.append({
            "narrative": row["narrative"],
            "claim_id": row["claim_id"],
        })
with open("/tmp/claim_batch.json", "w") as out:
    json.dump(rows, out, indent=2)
print("Wrote /tmp/claim_batch.json", len(rows), "claims")
PY

python ../scripts/simulate_text_path.py --batch /tmp/claim_batch.json --mode handoff
```

---

## HTML report contents

Generated by `scripts/simulate_text_path.py` using `templates/text_path_report.html`:

| Section | Source |
|---------|--------|
| Run metadata | mode, URLs, health, git SHA |
| Input batch | `narrative`, `claim_id`, `source_type` |
| Per-claim analysis | `/analyze` → label, confidence, `needs_review`, **extracted component** |
| Pareto | `/trends` → `by_label`, `by_component`, `overcycle_share` |
| Handoff | `/handoff` → full `RcaHandoff` including **`component`** |
| Subscriber | `/handoff/execute` → 5-Why whys + `structure_check` + 8D draft |
| Review queue | claims with `needs_review=true` |
| Embedded JSON | full captured API payloads (offline replay) |

---

## Implementation review (read-only)

Audit of this guide’s recommendations against the repo **as of June 2026**. The original audit was read-only; a follow-up pass (June 2026) then landed three items — `claims.csv` regenerated `component`-only, `--exclude-needs-review` triage on `/handoff`, and the `component_alias.py` engineering-retrieval map — reflected in the ✅ rows below.

### Completed ✅

| Recommendation | Evidence |
|----------------|----------|
| **`component`-only customer ingest** | `ClaimNarrative` has `narrative` / `claim_id` / `source_type` only — no `part_number` (`CLaimLens/claimlens/schema.py`) |
| **`component`-only extraction** | `extract.py` gazetteers → `ExtractedFields.component`; no BOM fields on API output |
| **`RcaHandoff` contract** | `component`, `problem_statement`, `anomaly_label`, `claim_count`, `share`, `target_endpoints` (`handoff.py`, `schema.py`) |
| **Subscriber accepts handoff** | `ProblemBody.component` + LangGraph scopes RAG/SQL by component (`QualityMind-RAG/app/api/quality_routes.py`, `quality_langgraph.py`) |
| **HTTP client + SSRF guard** | `qualitymind_client.py` → `/quality/five-why` + `/quality/draft-8d`; partial-failure safe |
| **Simulation orchestrator** | `scripts/simulate_text_path.py` — modes `trends` / `handoff` / `execute`, stdlib-only |
| **HTML report template** | `templates/text_path_report.html`; output under `reports/` (gitignored via `reports/.gitignore`) |
| **Mode D mock subscriber** | Orchestrator writes HTML when subscriber `/health` fails |
| **`needs_review` flag** | Classifier + review-queue section in HTML report |
| **Sample batch (no BOM fields)** | `SAMPLE_BATCH` in orchestrator uses narrative-only payloads |
| **Dev `structure_check`** | QualityMind attaches validation when `ENVIRONMENT=development` |
| **CSV generator schema** | `generate_sample_data.py` emits `component` column only (no `part_number` in row dict) |
| **Dev CSV corpus regenerated** | On-disk `data/claims.csv` regenerated → header `claim_id` / `date` / `vin` / `component` / `narrative` / `label`; matches generator |
| **Low-confidence triage in handoff** | `--exclude-needs-review` (orchestrator) → `?exclude_needs_review=` on `/handoff` + `/handoff/execute`; `build_handoff(exclude_needs_review=…)` drops flagged claims pre-trend (`handoff.py`, `api.py`) |
| **Component-scoped engineering retrieval** | `component_alias.py` resolves the descriptive `component` for QualityMind's engineering SQL join; 5-Why + 8D gather nodes use it (`QualityMind-RAG/app/services/component_alias.py`, `quality_langgraph.py`) |

### Partial 🔄

| Item | Status | Gap |
|------|--------|-----|
| **End-to-end live execute** | Orchestrator + curl documented; sample run exists (`reports/mode-c.html`) | Not in CI; [quality-feedback.md](quality-feedback.md) still marks localhost E2E ⏳ |
| **RAGAS baseline** | `QualityMind-RAG/evaluate.py` + `eval_metrics.py` exist | No pinned baseline artifact under `reports/`; not gated in portfolio CI |
| **Multi-source Pareto** | `by_source` on `/trends` when `source_type` set | Not reflected in default sample batch or orchestrator examples |

### Not started / operational ⏳

| Item | Notes |
|------|-------|
| **QualityMind Pinecone + DB seeded** | Operational step — required for non-empty `evidence_source` in live execute |
| **Multi-trend handoff queue** | Still dominant-trend only (`build_handoff`) |
| **Async retry / replay queue** | Synchronous HTTP; 502 if subscriber down |
| **Portfolio CI for simulation** | No workflow at repo root; per-repo CI runs unit tests only |
| **Production auth / rate limits** | Optional keys documented; deferred per guardrails |
| **Real warranty data** | Synthetic corpus only — by design in dev phase |

---

## Improvement points

Prioritized follow-ups surfaced by the review. These are **documentation and process** items unless noted as code.

| Priority | Improvement | Rationale | Owner |
|----------|-------------|-----------|-------|
| **P0 ✅** | Regenerate `CLaimLens/data/claims.csv` | Done — on-disk CSV now `component`-only, matches generator | CLaimLens |
| **P0** | Seed QualityMind Pinecone + Postgres per QM README | Unblocks credible 5-Why citations in mode C | QualityMind |
| **P1** | Run and pin `simulate_text_path.py --mode execute` as dev sign-off | Closes E2E gap; update `quality-feedback.md` when green | Both |
| **P1** | Pin RAGAS output to `reports/ragas-baseline-<date>.json` after first full eval | Closes “RAGAS baseline not pinned” gap | QualityMind |
| **P2 ✅** | Add `--exclude-needs-review` to orchestrator (optional filter before `/handoff`) | Done — flag → `?exclude_needs_review=`; `build_handoff` drops flagged claims pre-trend | Portfolio / CLaimLens |
| **P2** | Pass `X-API-Key` in orchestrator when `CLAIMLENS_API_KEY` / `QUALITYMIND_API_KEY` set | Auth path untested by simulation script today | Portfolio |
| **P2 ✅** | Component alias map for engineering Text-to-SQL retrieval | Done — `component_alias.py` resolves descriptive `component` for NCR/SPC joins; handoff stays `component`-only | QualityMind |
| **P3** | Portfolio CI: `simulate_text_path.py --mode handoff` with publisher up (or pytest smoke) | Catches contract regressions without OpenAI cost | Portfolio |
| **P3** | Multi-trend handoff (top-N Pareto) | Product gap — engineer must confirm single dominant trend manually | CLaimLens |
| **Deferred** | Production auth, real data, async queue | Out of dev/analytical scope per guardrails | — |

---

## Gaps vs impact

Track status in [quality-feedback.md](quality-feedback.md). Status column reflects the [implementation review](#implementation-review-read-only) above.

| Gap | Impact if unfixed | Severity | Owner | Status | Mitigation today |
|-----|-------------------|----------|-------|--------|------------------|
| **Orchestrator + HTML report** | Manual curl-only demos | Medium | Portfolio | ✅ | `scripts/simulate_text_path.py` + `templates/text_path_report.html` |
| **`component`-only handoff contract** | Engineering identifiers leaking into customer path | High | Both | ✅ | Code + tests on both sides; handoff carries `component` only |
| **QualityMind Pinecone / DB not seeded** | Empty `evidence_source` in live 5-Why | High | QualityMind | ⏳ | Upload PFMEA/CAPA; seed DB per QM README |
| **End-to-end live execute routine** | Integration regressions found late | Medium | Both | 🔄 | Orchestrator exists; not CI-gated; one sample report in `reports/` |
| **RAGAS baseline not pinned** | RAG regressions undetected | Medium | QualityMind | ⏳ | Run `QualityMind-RAG/evaluate.py`; save output under `reports/` |
| **Component-scoped engineering join** | SQL may miss engineering-DB rows scoped by component | Medium | QualityMind | ✅ | `component_alias.py` resolves the descriptive `component` for engineering retrieval; handoff stays `component`-only |
| **Stale `claims.csv` on disk** | Doc/code drift for corpus users | Low | CLaimLens | ✅ | Regenerated — `component`-only header |
| **Low-confidence in handoff batch** | `needs_review` skews Pareto | Medium | CLaimLens | ✅ | `--exclude-needs-review` → `?exclude_needs_review=` drops flagged claims pre-trend |
| **Single dominant trend only** | `#2` driver never escalated | Low | CLaimLens | ⏳ | Engineer confirms `/trends` before execute |
| **No async retry queue** | Subscriber down → 502 | Low (dev) | Both | ⏳ | Restart QM; re-run execute |
| **OpenAI cost per execute** | 5-Why + 8D ≈ 2 LLM chains | Low (dev) | Both | — | Use `--mode handoff` first |
| **Simulation script auth headers** | Auth-enabled dev untested | Low | Portfolio | ⏳ | Keys optional; orchestrator omits `X-API-Key` today |
| **Production auth** | Open APIs unsafe off localhost | High (prod) | Both | ⏳ deferred | API keys in prod only |
| **Real warranty data** | No prod-like volume validation | High (prod) | Portfolio | ⏳ deferred | Synthetic corpus only |

### Recommended closure order (dev)

1. ✅ `claims.csv` regenerated (`component`-only); seed QualityMind docs/DB still needed (**unblocks credible mode C**)
2. Green run: `--mode handoff` → `--mode execute` on sample batch; record in `quality-feedback.md`
3. Pin RAGAS + simulation HTML artifacts under `reports/` (gitignored)
4. P2 improvements (needs-review filter, auth headers, alias map) as needed
5. Production hardening after analytical sign-off

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| CLaimLens 503 "Model not trained" | Missing `models/anomaly_clf.joblib` | `python evaluate.py` |
| `/handoff` 404 | No overcycle in batch | Add soft_reset / cloud_sync narratives |
| `/handoff/execute` 502 | QM down or all endpoints failed | Start port 8000; check `QUALITYMIND_BASE_URL` |
| QM 503 on `/quality/five-why` | Missing `OPENAI_API_KEY` | Fill `.env` |
| Empty RAG citations | Pinecone empty | Upload docs per QM README |
| SSRF on handoff | Bad base URL | `http://127.0.0.1:8000` |
| Slow execute (>60s) | LangGraph + RAG | Increase `--timeout` |
| `structure_check.valid: false` | Agent output invalid | Fix retrieval/prompts; dev only |
| `component` is null | Narrative lacks component keywords | Use TCU/gateway/modem/infotainment language |

---

## Success checklist

Use after a local run. “Code ✅” = implemented in repo; “Run ☐” = verify on your machine.

| Check | Code | Run |
|-------|------|-----|
| `/trends` on 10+ narratives → sensible `by_component` Pareto | ✅ | ☐ |
| `/handoff` returns descriptive **`component`** (not an engineering id) | ✅ | ☐ |
| `/handoff/execute` → ≥1 `"status": "ok"` in `qualitymind_response` | ✅ | ☐ |
| 5-Why has ≥3 `whys` with `evidence_source` (needs QM seed) | ✅ | ☐ |
| `structure_check.valid: true` in dev | ✅ | ☐ |
| `needs_review` claims visible in HTML review queue | ✅ | ☐ |
| HTML report opens offline, no embedded secrets | ✅ | ☐ |
| `data/claims.csv` matches generator schema (`component`-only header) | ✅ | ☐ |

---

## Related docs

| Document | Role |
|----------|------|
| [TEXT-NARRATIVE-PATH.md](TEXT-NARRATIVE-PATH.md) | Architecture + industry context |
| [QUALITY-ENGG-GUARDRAILS.md](QUALITY-ENGG-GUARDRAILS.md) | Handoff contract + security |
| [quality-feedback.md](quality-feedback.md) | Implementation changelog |
| [CLaimLens/README.md](CLaimLens/README.md) | Publisher API |
| [QualityMind-RAG/README.md](QualityMind-RAG/README.md) | Subscriber API (incl. engineering SQL routes) |

---

## Summary

Simulate the text path by running **CLaimLens** (publisher) and **QualityMind-RAG** (subscriber) on localhost. Customer batches need only **`narrative`** (+ optional `claim_id`, `source_type`); **`component`** is extracted upstream and carried in **`RcaHandoff`**.

**What’s done:** contract, orchestrator, HTML template, and mock mode are in the repo. **What’s left for a credible live demo:** regenerate CSV if stale, seed QualityMind RAG/DB, then run `--mode handoff` → `--mode execute` and pin artifacts under `reports/`. See [Improvement points](#improvement-points).
