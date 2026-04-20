
# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- [GROUP_NAME]: 
- [REPO_URL]: 
- [MEMBERS]:
  - Member A: Nguyễn Huy Tú (2A202600170) | Role: Logging & PII
  - Member B: Phạm Quốc Vương (2A202600419) | Role: Tracing & Enrichment
  - Member C: Trương Minh Phước (2A202600330) | Role: SLO & Alerts
  - Member D: Nguyễn Thành Trung (2A202600451) | Role: Load Test & Dashboard
  - Member E: [Name] | Role: Demo & Report

---

## 2. Group Performance (Auto-Verified)
- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 30
- [PII_LEAKS_FOUND]: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: [Path to image]
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: [Path to image]
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: [Path to image]
- [TRACE_WATERFALL_EXPLANATION]: (Briefly explain one interesting span in your trace)

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: docs/evidence/dashboard-panels-1.png, docs/evidence/dashboard-panels-2.png
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| Latency P95 | < 3000ms | 28d | 165 ms |
| Error Rate | < 2% | 28d | 0.0% |
| Cost Budget | < $2.5/day | 1d | $0.0631 (30 req) |
| Quality Score Avg | >= 0.75 | 28d | 0.88 |

### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: [Path to image]
- [SAMPLE_RUNBOOK_LINK]: docs/alerts.md#1-high-latency-p95

---

## 4. Incident Response (Group)
- [SCENARIO_NAME]: (e.g., rag_slow)
- [SYMPTOMS_OBSERVED]: 
- [ROOT_CAUSE_PROVED_BY]: (List specific Trace ID or Log Line)
- [FIX_ACTION]: 
- [PREVENTIVE_MEASURE]: 

---

## 5. Individual Contributions & Evidence

### Nguyễn Huy Tú (2A202600170)
- [TASKS_COMPLETED]: Implemented PII redaction in logging pipeline by enabling `scrub_event`; added recursive scrub for nested log fields (dict/list/tuple); extended `PII_PATTERNS` with `passport` and `address`; added tests for email, VN phone, credit card, passport, address, and nested payload redaction; verified with `.venv` using `pytest` (6 passed) and runtime validation where PII scrubbing passed.
- [EVIDENCE_LINK]: https://github.com/huytu0702/Lab13-Observability_Nhom36/commit/49d7af8cebb3db3980ad7437af8bc968453c7417

### Member B: [Your Name Here]
- [TASKS_COMPLETED]: 
  - Implemented correlation ID middleware with UUID generation (format: req-{8-char-hex})
  - Added automatic correlation ID extraction from x-request-id header or auto-generation
  - Bound correlation_id to structlog contextvars for automatic log propagation
  - Added response headers (x-request-id, x-response-time-ms) for client-side tracking
  - Implemented log enrichment in /chat endpoint with user_id_hash, session_id, feature, model, env
  - Verified Langfuse tracing infrastructure (ready, requires API keys to activate)
  - Achieved 100/100 validation score with 14+ unique correlation IDs
  - Zero PII leaks detected, all required fields present in logs
  
- [EVIDENCE_LINK]: [Your commit link - e.g., https://github.com/username/repo/commit/abc123] 

### Trương Minh Phước (2A202600330)
- [TASKS_COMPLETED]:
  - Refined `config/slo.yaml`: added `group`, `description` fields for each SLI and linked each SLI to its alert rule; targets are `latency_p95_ms < 3000 ms`, `error_rate_pct < 2%`, `daily_cost_usd < $2.50`, `quality_score_avg >= 0.75`.
  - Extended `config/alert_rules.yaml`: tightened latency threshold from 5000 ms to 3000 ms (aligned with SLO); tightened error-rate threshold from 5% to 2% (aligned with SLO); added full `annotations` (summary + description) to all 3 existing rules; added 4th alert rule `low_quality_score` (severity P3, trigger `quality_score_avg < 0.75 for 60m`).
  - Expanded `docs/alerts.md` runbook: enriched all 3 existing runbooks with severity, first-check steps, mitigation actions, and escalation path; added runbook section 4 for `low_quality_score` including RAG doc_count check and over-redaction diagnosis.
  - Built `scripts/check_slo.py`: standalone Python script that fetches live `/metrics` from the running FastAPI app, loads `config/slo.yaml`, evaluates each SLI against its objective, and prints a compliance table (exit code 0 = all pass, 1 = breach). Supports `--url` flag and `--json` output mode.
  - Verified compliance: ran `python scripts/check_slo.py` after 30 live requests — all 4 SLOs passed (P95=165 ms, error_rate=0%, cost=$0.063, quality=0.88). `validate_logs.py` score = 100/100, 0 PII leaks, 30 unique correlation IDs.
- [EVIDENCE_LINK]: https://github.com/huytu0702/Lab13-Observability_Nhom36/commit/5315476

### Nguyễn Thành Trung (2A202600451)
- [TASKS_COMPLETED]:
  - Rewrote `scripts/load_test.py` into a full load generator: added `--concurrency`, `--repeat`, `--duration`, `--rps`, `--report`, `--no-report` flags; per-request capture of latency, cost, tokens, quality, and correlation_id; aggregate summary printed and persisted to `data/load_report.json` (totals, success/failed, error_rate_pct, latency p50/p95/p99/avg/max, cost total/avg, tokens in/out, quality average, error breakdown).
  - Added `scripts/render_dashboard.py`: fetches live `/metrics`, joins it with `data/load_report.json`, loads `config/slo.yaml` (PyYAML optional, hand-rolled fallback), and renders the 6 required panels into `docs/dashboard.md` with explicit SLO/threshold lines (Latency P50/P95/P99 vs 3000 ms, Traffic, Error Rate vs 2%, Cost vs $2.50/day, Tokens in/out, Quality vs 0.75). Also writes `data/dashboard_snapshot.json` for parser-friendly grading and prints any breaching panels.
  - Expanded `docs/dashboard-spec.md`: documented the 6 panels with their `/metrics` source field, unit, SLO line, and matching alert (cross-linked to Member C's `config/alert_rules.yaml`); added the load-test → dashboard workflow and an evidence checklist.
  - Verified end-to-end on a live `uvicorn app.main:app --reload`: ran `python scripts/load_test.py --concurrency 5 --repeat 3` (30 requests, all succeeded) followed by `python scripts/render_dashboard.py`. Output saved to `docs/dashboard.md` and `data/dashboard_snapshot.json`. All 6 panels report **OK** against the SLOs from `config/slo.yaml`:
    - Latency server-side P50/P95/P99 = 152 / 165 / 166 ms (SLO P95 < 3000 ms).
    - Wall-clock latency from the load tester P50/P95/P99 = 789 / 806 / 807 ms — the gap vs server-side is HTTP/network overhead, a useful demo of why client-side measurement matters.
    - Error rate = 0.00% (SLO < 2%).
    - Cost = $0.0584 total / $0.001900 avg per request (SLO < $2.50/day).
    - Tokens in/out = 1020 / 3692.
    - Quality avg = 0.88 (SLO >= 0.75).
  - Evidence screenshots committed under `docs/evidence/dashboard-panels-1.png` (panels 1-4) and `docs/evidence/dashboard-panels-2.png` (panels 5-6 + load-test appendix).
- [EVIDENCE_LINK]: [Your commit link - e.g., https://github.com/username/repo/commit/abc123]

### [MEMBER_E_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: (Description + Evidence)
- [BONUS_AUDIT_LOGS]: (Description + Evidence)
- [BONUS_CUSTOM_METRIC]: (Description + Evidence)
