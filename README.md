# Quality Engineering Portfolio

Umbrella workspace for the connected-vehicle / manufacturing quality projects.
**Each project folder is its own independent git repository** (cloned side by
side here) — they are excluded from this repo via [.gitignore](.gitignore) and
tracked separately. This root repo holds only the **cross-project glue**: the
publisher → subscriber simulation, shared guardrails, and the HTML report
orchestrator.

## Project folders (separate repos)

| Folder | Role | Repository |
|--------|------|------------|
| [CLaimLens/](CLaimLens/) | Warranty-narrative NLP for field quality & reliability RCA — **publisher** | https://github.com/vgandhi1/claimlens |
| [QualityMind-RAG/](QualityMind-RAG/) | AI-powered manufacturing quality engineering assistant (RAG + LangGraph) — **subscriber** | https://github.com/vgandhi1/QualityMind-RAG |
| [AutoClaim-VLM/](AutoClaim-VLM/) | Damage intelligence via vision-language models | https://github.com/vgandhi1/AutoClaim-VLM |
| [automotive-visual-qa-engine/](automotive-visual-qa-engine/) | Visual quality inspection & rework routing engine | https://github.com/vgandhi1/automotive-visual-qa-engine |
| [cell-to-pack/](cell-to-pack/) | Cell-to-pack vision orchestrator — ML/AI for EV battery assembly | https://github.com/vgandhi1/cell-to-pack |

## Cross-project glue (tracked here)

| Path | Role |
|------|------|
| [PUBLISHER-SUBSCRIBER-SIMULATION.md](PUBLISHER-SUBSCRIBER-SIMULATION.md) | CLaimLens → QualityMind-RAG text-path simulation guide |
| [TEXT-NARRATIVE-PATH.md](TEXT-NARRATIVE-PATH.md) | Architecture + industry context |
| [QUALITY-ENGG-GUARDRAILS.md](QUALITY-ENGG-GUARDRAILS.md) | Handoff contract + security guardrails |
| [scripts/simulate_text_path.py](scripts/simulate_text_path.py) | Stdlib-only orchestrator → self-contained HTML report |
| [templates/text_path_report.html](templates/text_path_report.html) | Report template |
| `reports/` | Generated HTML output (gitignored) |

## Working with the sub-repos

Each folder is cloned/committed independently — run git inside the folder:

```bash
git -C CLaimLens status
git -C QualityMind-RAG status
```

Changes to a project belong in that project's own repository; only the glue
files above are committed at this root.
