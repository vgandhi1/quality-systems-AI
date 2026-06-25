# Warranty Adjudication Path — Dealership Payment Intelligence

**Portfolio area:** Quality Engineering · ADJUDICATION PATH  
**Project:** [warranty/](warranty/) (tracked in quality-systems-AI umbrella repo)  
**Guardrails:** [QUALITY-SYSTEMS-GUARDRAILS.md](QUALITY-SYSTEMS-GUARDRAILS.md)  
**Phase:** T2 release-ready (dev environment) — not production payment software  
**Deck:** [warranty/presentation.html](warranty/presentation.html) (GitHub Pages on push to `main`)  
**Last updated:** June 2026

---

## Purpose

Dealerships submit warranty **payment claims** as structured forms, OBD-II diagnostics, and supporting documents. Human adjusters cross-check OEM policy, VIN eligibility, labor matrices, and fraud signals before authorizing payment.

The **Adjudication Path** automates single-claim payment routing:

1. **Intake** — extract DTCs, parts, labor, and cost from claim bundle  
2. **Policy** — verify coverage against OEM warranty policy (metadata-filtered search)  
3. **Fraud** — score labor variance and dealership velocity  
4. **Adjudicate** — route to `AUTO_APPROVE`, `MISSING_DATA`, or `HUMAN_REVIEW`  
5. **Escalate** (optional) — send `HUMAN_REVIEW` claims to QualityMind-RAG for engineering RCA  

---

## Boundary rules (do not cross without explicit contract)

| Path | Domain | Output |
|------|--------|--------|
| **CLaimLens** (text path) | Field warranty **narratives** → batch Pareto | `RcaHandoff` with `anomaly_label` |
| **warranty** (adjudication path) | Dealership **payment** claims | `AUTO_APPROVE` / `MISSING_DATA` / `HUMAN_REVIEW` |
| **QualityMind-RAG** | Manufacturing RCA | 5-Why, 8D, CAPA |
| **AutoClaim-VLM** (vision path) | Insurance **damage photos** | VLM routing to adjuster |

- warranty does **not** use the CLaimLens `RcaHandoff` schema.  
- warranty escalations use `RcaEscalation` (claim-level, no batch Pareto fields).  
- Do not share routing enums or schemas with AutoClaim-VLM.

---

## Architecture

```text
Dealership claim bundle
        │
        ▼
  Orchestrator (Intake → Policy → Fraud → Adjudicator)
        │
        ├── AUTO_APPROVE ──► ERP authorize (future)
        ├── MISSING_DATA ──► pause / notify dealership
        └── HUMAN_REVIEW ──► adjuster UI
                    │
                    └── RcaEscalation ──► QualityMind /quality/five-why
```

---

## Cross-project contracts

### warranty → QualityMind (`RcaEscalation`)

Emitted when adjudicator routes `HUMAN_REVIEW` and engineering RCA is requested:

```python
{
    "problem_statement": str,   # claim summary for 5-Why / 8D
    "component": str,             # descriptive part name from intake
    "claim_id": str,
    "decision_route": "HUMAN_REVIEW",
    "target_endpoints": ["/quality/five-why", "/quality/draft-8d"]
}
```

**Not in escalation:** `anomaly_label`, `claim_count`, `share` (those belong to CLaimLens `RcaHandoff`).

### CLaimLens → warranty (future, optional)

A dominant field overcycle trend with high dealership claim volume may enqueue claims for adjudication review. This is **not** implemented — document only.

---

## API (dev)

```bash
cd warranty && uv sync --extra api --extra dev
uv run warranty-api
# Open http://localhost:8080/docs
# POST /adjudicate/dry-run  {"scenario": "auto_approve"}
# POST /escalate/handoff    <claim_state JSON>
# POST /escalate/execute    <claim_state JSON>  # requires QUALITYMIND_BASE_URL
```

See [warranty/README.md](warranty/README.md) for routing thresholds, LAN access, and test commands.  
Visual overview: [warranty/presentation.html](warranty/presentation.html).

---

## Out of scope (deferred)

- Live ERP / SAP payment integration  
- Temporal long-running workflows  
- Multimodal video intake  
- Production Qdrant cluster (stub exists; keyword search is default)  
- AgentForge preset registration  

See [warranty/doc.md](warranty/doc.md) for the full implementation roadmap.
