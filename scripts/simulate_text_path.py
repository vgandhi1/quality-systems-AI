#!/usr/bin/env python3
"""Publisher -> Subscriber text-path simulation orchestrator.

Drives the CLaimLens (publisher) -> QualityMind-RAG (subscriber) HTTP handoff
described in PUBLISHER-SUBSCRIBER-SIMULATION.md and renders a single
self-contained HTML report. Stdlib only -- no third-party deps, so it runs
without activating either project's venv.

Modes (matching the simulation guide):
    trends   -> mode A: /analyze + /trends only (publisher, no OpenAI cost)
    handoff  -> mode B: + /handoff dry-run (contract preview, no subscriber)
    execute  -> mode C: + /handoff/execute (live subscriber, OpenAI cost)

Mock mode D is automatic: if --mode execute but the subscriber /health fails
(no OPENAI_API_KEY, port down, etc.), the subscriber section renders a
placeholder panel and the report is still written. Use this in CI / portfolio
runs without API keys.

Examples:
    python scripts/simulate_text_path.py                      # execute, default sample batch
    python scripts/simulate_text_path.py --mode handoff       # contract preview, no keys needed
    python scripts/simulate_text_path.py --batch /tmp/b.json --out reports/demo.html
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "text_path_report.html"
REPORTS_DIR = ROOT / "reports"

DEFAULT_PUBLISHER = "http://127.0.0.1:8001"
DEFAULT_SUBSCRIBER = os.environ.get("QUALITYMIND_BASE_URL", "http://127.0.0.1:8000")

# Overcycle-themed synthetic batch so /handoff finds a dominant trend.
SAMPLE_BATCH = [
    {"narrative": "TCU watchdog soft reset after ignition cycle", "claim_id": "WC-1001"},
    {"narrative": "Soft reset again on telematics unit every morning", "claim_id": "WC-1002"},
    {"narrative": "Gateway fails cloud sync retries exhausted overnight", "claim_id": "WC-1003"},
    {"narrative": "Infotainment OTA download stalls map sync never completes", "claim_id": "WC-1004"},
    {"narrative": "No fault found bench test passed all checks", "claim_id": "WC-1005"},
]


# ───────────────────────── HTTP (stdlib) ─────────────────────────

def _request(method: str, url: str, body: object | None, timeout: float) -> tuple[int, object]:
    """Return (status_code, parsed_json_or_text). Never raises on HTTP errors."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, _maybe_json(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        return exc.code, _maybe_json(raw)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return 0, {"error": str(exc)}


def _maybe_json(raw: str) -> object:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


def get(url: str, timeout: float) -> tuple[int, object]:
    return _request("GET", url, None, timeout)


def post(url: str, body: object, timeout: float) -> tuple[int, object]:
    return _request("POST", url, body, timeout)


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, capture_output=True, text=True, timeout=3,
        )
        return out.stdout.strip() or "n/a"
    except Exception:
        return "n/a"


# ───────────────────────── HTML helpers ─────────────────────────

def status_pill(status: str) -> str:
    cls = {"ok": "s-ok", "error": "s-error", "skipped": "s-skipped"}.get(status, "s-skipped")
    return f'<span class="pill-status {cls}">{escape(status)}</span>'


def meta_table(rows: list[tuple[str, str]]) -> str:
    return "".join(
        f"<tr><td class='mono'>{escape(k)}</td><td>{escape(str(v))}</td></tr>" for k, v in rows
    )


def input_rows(batch: list[dict]) -> str:
    out = []
    for i, c in enumerate(batch, 1):
        narr = escape((c.get("narrative") or "")[:90])
        src = escape(str(c.get("source_type") or "—"))
        out.append(
            f"<tr><td class='num'>{i}</td>"
            f"<td class='mono'>{escape(str(c.get('claim_id') or '—'))}</td>"
            f"<td>{narr}</td>"
            f"<td class='mono'>{src}</td></tr>"
        )
    return "".join(out)


def analysis_rows(analyzed: list[dict]) -> str:
    if not analyzed:
        return "<tr><td colspan='5' class='empty'>No /analyze results (publisher unreachable or skipped).</td></tr>"
    out = []
    for a in analyzed:
        cls = a.get("classification", {})
        ext = a.get("extracted", {})
        review = cls.get("needs_review")
        review_html = (
            "<span class='pill-status s-error'>review</span>" if review
            else "<span class='pill-status s-ok'>ok</span>"
        )
        conf = cls.get("confidence")
        conf_str = f"{conf:.2f}" if isinstance(conf, (int, float)) else "—"
        out.append(
            f"<tr><td class='mono'>{escape(str(a.get('claim_id') or '—'))}</td>"
            f"<td>{escape(str(cls.get('label_name') or cls.get('label') or '—'))}</td>"
            f"<td class='num'>{conf_str}</td>"
            f"<td>{review_html}</td>"
            f"<td>{escape(str(ext.get('component') or '—'))}</td></tr>"
        )
    return "".join(out)


def pareto_bars(trends: dict | None) -> str:
    if not isinstance(trends, dict) or "by_label" not in trends:
        return "<div class='empty'>No trends data.</div>"
    parts = [
        '<div class="metrics">'
        f'<div class="metric"><div class="n">{trends.get("total_claims", 0)}</div><div class="l">total claims</div></div>'
        f'<div class="metric"><div class="n">{trends.get("overcycle_share", 0):.0%}</div><div class="l">overcycle share</div></div>'
        f'<div class="metric"><div class="n">{len(trends.get("by_label", []))}</div><div class="l">labels seen</div></div>'
        f'<div class="metric"><div class="n">{len(trends.get("by_component", []))}</div><div class="l">components</div></div>'
        '</div>'
    ]
    for title, key in (("By label", "by_label"), ("By component", "by_component"),
                       ("By failure mode", "by_failure_mode")):
        buckets = trends.get(key, [])
        if not buckets:
            continue
        parts.append(f'<div class="chart"><div class="ct">{title}</div>')
        top = max((b.get("count", 0) for b in buckets), default=1) or 1
        for b in buckets:
            pct = (b.get("count", 0) / top) * 100
            parts.append(
                f'<div class="crow"><div class="cl">{escape(str(b.get("key")))}</div>'
                f'<div class="track"><i style="width:{pct:.1f}%"></i></div>'
                f'<div class="cv">{b.get("count")} · {b.get("share", 0):.0%}</div></div>'
            )
        parts.append("</div>")
    return "".join(parts)


def handoff_block(handoff: dict | None, status: int) -> str:
    if not isinstance(handoff, dict) or "problem_statement" not in handoff:
        detail = handoff.get("detail") if isinstance(handoff, dict) else handoff
        return (
            f'<div class="banner err">/handoff returned HTTP {status}: '
            f'{escape(str(detail))}</div>'
        )
    rows = [
        ("problem_statement", handoff.get("problem_statement")),
        ("component", handoff.get("component")),
        ("anomaly_label", handoff.get("anomaly_label")),
        ("claim_count", handoff.get("claim_count")),
        ("share", handoff.get("share")),
        ("target_endpoints", ", ".join(handoff.get("target_endpoints", []))),
    ]
    body = "".join(
        f"<tr><td class='mono'>{escape(k)}</td><td>{escape(str(v))}</td></tr>" for k, v in rows
    )
    return f"<table>{body}</table>"


def _whys_html(analysis: dict) -> str:
    whys = analysis.get("whys") or analysis.get("five_whys") or []
    if not whys:
        return "<div class='empty'>No whys returned.</div>"
    out = []
    for i, w in enumerate(whys, 1):
        if isinstance(w, dict):
            q = w.get("why") or w.get("statement") or w.get("question") or json.dumps(w)
            ev = w.get("evidence_source") or w.get("evidence") or ""
        else:
            q, ev = str(w), ""
        ev_html = f"<div class='ev'>evidence: {escape(str(ev))}</div>" if ev else \
            "<div class='ev'>evidence: — (RAG not seeded)</div>"
        out.append(f"<div class='why'><span class='q'>Why {i}:</span> {escape(str(q))}{ev_html}</div>")
    conf = analysis.get("confidence_score")
    if isinstance(conf, (int, float)):
        out.append(f"<div class='ev'>confidence_score: {conf:.2f}</div>")
    return "".join(out)


def subscriber_block(mode: str, sub_health_ok: bool, execute_resp: dict | None,
                     execute_status: int) -> str:
    if mode != "execute":
        return ('<div class="banner dry">Dry-run mode (' + escape(mode) +
                '). Subscriber not called. Re-run with --mode execute against a live '
                'QualityMind-RAG to populate 5-Why / 8D.</div>')
    if not sub_health_ok:
        return ('<div class="banner dry">MOCK (mode D): subscriber unreachable or degraded — '
                'no OPENAI_API_KEY / port down. Publisher payload above is valid; the live '
                '5-Why / 8D panel needs a running QualityMind-RAG with keys configured.</div>')
    if not isinstance(execute_resp, dict):
        return f'<div class="banner err">/handoff/execute HTTP {execute_status}: {escape(str(execute_resp))}</div>'

    qm = execute_resp.get("qualitymind_response")
    if not isinstance(qm, dict):
        detail = execute_resp.get("detail", execute_resp)
        return (f'<div class="banner err">/handoff/execute HTTP {execute_status} — '
                f'no per-endpoint results: {escape(str(detail))}</div>')

    parts = ['<div class="banner live">Live subscriber response.</div>']
    for endpoint, res in qm.items():
        st = res.get("status", "?") if isinstance(res, dict) else "?"
        parts.append(f'<h2 style="font-size:20px">{escape(endpoint)} {status_pill(st)}</h2>')
        if st != "ok":
            parts.append(f"<div class='empty'>{escape(str(res.get('detail', res)))}</div>")
            continue
        resp = res.get("response", {})
        if "five-why" in endpoint:
            analysis = resp.get("analysis", {})
            parts.append(_whys_html(analysis))
            sc = resp.get("structure_check")
            if sc:
                ok = sc.get("valid")
                parts.append(
                    f'<div class="ev">structure_check.valid: '
                    f'{status_pill("ok" if ok else "error")} '
                    f'errors={escape(str(sc.get("errors", [])))}</div>'
                )
        elif "draft-8d" in endpoint:
            draft = resp.get("draft", {})
            body = "".join(
                f"<tr><td class='mono'>{escape(str(k))}</td><td>{escape(str(v))}</td></tr>"
                for k, v in (draft.items() if isinstance(draft, dict) else [])
            )
            parts.append(f"<table>{body}</table>" if body else "<div class='empty'>Empty draft.</div>")
    return "".join(parts)


def review_queue(analyzed: list[dict]) -> str:
    flagged = [a for a in analyzed if a.get("classification", {}).get("needs_review")]
    if not flagged:
        return "<div class='empty'>No claims flagged needs_review. ✅</div>"
    rows = "".join(
        f"<tr><td class='mono'>{escape(str(a.get('claim_id') or '—'))}</td>"
        f"<td>{escape((a.get('narrative') or '')[:80])}</td>"
        f"<td class='num'>{a.get('classification', {}).get('confidence', 0):.2f}</td></tr>"
        for a in flagged
    )
    return (f"<table><tr><th>claim_id</th><th>narrative</th><th>conf.</th></tr>{rows}</table>"
            f"<div class='empty'>{len(flagged)} claim(s) need engineer review before action.</div>")


def errors_block(errs: list[str]) -> str:
    if not errs:
        return "<div class='empty'>No errors or skips. ✅</div>"
    return "".join(f'<div class="banner err">{escape(e)}</div>' for e in errs)


def mode_banner(mode: str) -> str:
    txt = {
        "trends": "Mode A — analyze + Pareto only. No subscriber, no OpenAI cost.",
        "handoff": "Mode B — handoff contract preview. No subscriber call.",
        "execute": "Mode C — live publisher → subscriber. OpenAI cost if keys configured.",
    }.get(mode, mode)
    return f'<div class="banner dry">{escape(txt)}</div>'


# ───────────────────────── orchestration ─────────────────────────

def run(args: argparse.Namespace) -> int:
    batch = SAMPLE_BATCH
    if args.batch:
        batch = json.loads(Path(args.batch).read_text())
        if not isinstance(batch, list):
            print("error: --batch JSON must be a list of claim objects", file=sys.stderr)
            return 2

    pub, sub = args.publisher.rstrip("/"), args.subscriber.rstrip("/")
    t = args.timeout
    errors: list[str] = []
    captured: dict[str, object] = {}

    # 1. health
    pub_status, pub_health = get(f"{pub}/health", t)
    pub_ok = pub_status == 200
    if not pub_ok:
        errors.append(f"Publisher /health failed (HTTP {pub_status}). Start CLaimLens on {pub}.")
    captured["publisher_health"] = pub_health

    sub_status, sub_health = (0, None)
    sub_ok = False
    if args.mode == "execute":
        sub_status, sub_health = get(f"{sub}/health", t)
        sub_ok = sub_status == 200
        captured["subscriber_health"] = sub_health
        if not sub_ok:
            errors.append(f"Subscriber /health failed (HTTP {sub_status}) — entering MOCK (mode D).")
        elif isinstance(sub_health, dict) and sub_health.get("status") == "degraded":
            cfg = sub_health.get("configuration", {})
            if not cfg.get("openai_configured"):
                errors.append("Subscriber degraded: OPENAI_API_KEY not configured — /handoff/execute will 502.")

    # 2. per-claim analyze (for analysis table + review queue)
    analyzed: list[dict] = []
    if pub_ok:
        for c in batch:
            st, body = post(f"{pub}/analyze", c, t)
            if st == 200 and isinstance(body, dict):
                analyzed.append(body)
            else:
                errors.append(f"/analyze failed for {c.get('claim_id', '?')} (HTTP {st}).")
    captured["analyzed"] = analyzed

    # 3. trends
    trends = None
    if pub_ok:
        st, trends = post(f"{pub}/trends", batch, t)
        if st != 200:
            errors.append(f"/trends failed (HTTP {st}).")
            trends = None
    captured["trends"] = trends

    # 4. handoff (skip in mode trends)
    qs = "?exclude_needs_review=true" if args.exclude_needs_review else ""
    handoff, handoff_status = None, 0
    if pub_ok and args.mode in ("handoff", "execute"):
        handoff_status, handoff = post(f"{pub}/handoff{qs}", batch, t)
        if handoff_status == 404:
            errors.append("/handoff 404 — no overcycle anomalies in batch; add soft_reset/cloud_sync narratives.")
        elif handoff_status != 200:
            errors.append(f"/handoff failed (HTTP {handoff_status}).")
    captured["handoff"] = handoff

    # 5. execute (mode execute + subscriber reachable)
    execute_resp, execute_status = None, 0
    if pub_ok and args.mode == "execute" and sub_ok:
        execute_status, execute_resp = post(f"{pub}/handoff/execute{qs}", batch, t)
        if execute_status == 502:
            errors.append("/handoff/execute 502 — all subscriber endpoints failed (likely missing OPENAI_API_KEY).")
        elif execute_status != 200:
            errors.append(f"/handoff/execute failed (HTTP {execute_status}).")
    captured["handoff_execute"] = execute_resp

    # ── render ──
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%d-%H%M%S")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    tmpl = TEMPLATE.read_text()
    repl = {
        "{{RUN_ID}}": run_id,
        "{{MODE}}": args.mode,
        "{{TIMESTAMP}}": timestamp,
        "{{PUBLISHER_URL}}": pub,
        "{{SUBSCRIBER_URL}}": sub if args.mode == "execute" else "n/a (dry-run)",
        "{{MODE_BANNER}}": mode_banner(args.mode),
        "{{META_ROWS}}": meta_table([
            ("run_id", run_id),
            ("mode", args.mode),
            ("batch_size", len(batch)),
            ("publisher", pub),
            ("publisher_health", "ok" if pub_ok else f"FAIL ({pub_status})"),
            ("subscriber", sub if args.mode == "execute" else "not called"),
            ("subscriber_health", ("ok" if sub_ok else f"unavailable ({sub_status})")
                if args.mode == "execute" else "n/a"),
            ("live_or_mock", "live" if (args.mode == "execute" and sub_ok) else "mock/dry-run"),
            ("git_sha", _git_sha()),
        ]),
        "{{INPUT_ROWS}}": input_rows(batch),
        "{{ANALYSIS_ROWS}}": analysis_rows(analyzed),
        "{{PARETO}}": pareto_bars(trends),
        "{{HANDOFF}}": handoff_block(handoff, handoff_status) if args.mode != "trends"
            else "<div class='empty'>Skipped in mode trends.</div>",
        "{{SUBSCRIBER}}": subscriber_block(args.mode, sub_ok, execute_resp, execute_status),
        "{{REVIEW_QUEUE}}": review_queue(analyzed),
        "{{ERRORS}}": errors_block(errors),
        "{{EMBEDDED_JSON}}": escape(json.dumps(captured, indent=2, default=str)),
    }
    html = tmpl
    for k, v in repl.items():
        html = html.replace(k, v)

    out_path = Path(args.out) if args.out else REPORTS_DIR / f"text-path-{run_id}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)

    # console summary
    print(f"[simulate] mode={args.mode} batch={len(batch)} "
          f"publisher={'ok' if pub_ok else 'FAIL'} "
          f"subscriber={'live' if (args.mode == 'execute' and sub_ok) else 'mock/dry-run'}")
    if isinstance(handoff, dict) and handoff.get("problem_statement"):
        print(f"[simulate] handoff: {handoff['problem_statement']}")
    for e in errors:
        print(f"[simulate]   ! {e}")
    print(f"[simulate] report -> {out_path}")
    # Non-zero only if the publisher itself is down (the report is still useful otherwise).
    return 0 if pub_ok else 1


def main() -> int:
    p = argparse.ArgumentParser(description="CLaimLens -> QualityMind text-path simulation + HTML report.")
    p.add_argument("--batch", help="Path to JSON list of claim objects. Default: built-in overcycle sample.")
    p.add_argument("--mode", choices=("trends", "handoff", "execute"), default="execute",
                   help="trends=A, handoff=B, execute=C. Default: execute.")
    p.add_argument("--out", help="Output HTML path. Default: reports/text-path-<timestamp>.html")
    p.add_argument("--publisher", default=DEFAULT_PUBLISHER, help=f"CLaimLens base URL (default {DEFAULT_PUBLISHER}).")
    p.add_argument("--subscriber", default=DEFAULT_SUBSCRIBER,
                   help=f"QualityMind base URL (default {DEFAULT_SUBSCRIBER} / $QUALITYMIND_BASE_URL).")
    p.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout seconds (default 60).")
    p.add_argument("--exclude-needs-review", action="store_true",
                   help="Drop low-confidence needs_review claims before /handoff (guardrail: triage before RCA).")
    return run(p.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
