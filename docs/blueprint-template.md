
# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- `[GROUP_NAME]`: [Nhom 36]
- `[REPO_URL]`: [Lab13-Observability_Nhom36](https://github.com/huytu0702/Lab13-Observability_Nhom36.git)
- `[MEMBERS]`:
  - Member A: [Nguyễn Huy Tú] | Role: Dashboard UI, Langfuse & PII
  - Member B: [Phạm Quốc Vương] | Role: Tracing & Enrichment
  - Member C: [Trương Minh Phước] | Role: SLO & Alerts
  - Member D: [Nguyễn Thành Trung] | Role: Load Test & Dashboard
  - Member E: [Lương Hoàng Anh] | Role: Demo & Report

---

## 2. Group Performance (Auto-Verified)
- `[VALIDATE_LOGS_FINAL_SCORE]`: 100/100
- `[TOTAL_TRACES_COUNT]`: 30
- `[PII_LEAKS_FOUND]`: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- `[EVIDENCE_CORRELATION_ID_SCREENSHOT]` & `[EVIDENCE_PII_REDACTION_SCREENSHOT]`:
  [logs.png](https://github.com/huytu0702/Lab13-Observability_Nhom36/blob/main/docs/evidences/logs.png?raw=true)

- `[EVIDENCE_TRACE_WATERFALL_SCREENSHOT]`: [langfuse_2.png](https://github.com/huytu0702/Lab13-Observability_Nhom36/blob/main/docs/evidences/langfuse_2.png?raw=true)
- `[TRACE_WATERFALL_EXPLANATION]`: The `llm.generate` span inside the `agent.run` trace is the most interesting span. It captures the full LLM generation lifecycle including model name (`claude-sonnet-4-5`), input/output token counts (`input: 34, output: ~137`), estimated cost (`$0.002`), and a PII-safe preview of both the prompt and the response. The parent `agent.run` trace wraps both `rag.retrieve` (document retrieval) and `llm.generate` spans, giving a clear waterfall view of where latency is spent - retrieval vs generation. This hierarchical structure enables quick root-cause analysis: if latency spikes, we can immediately see whether the bottleneck is in RAG or LLM by comparing span durations.

### 3.2 Dashboard & SLOs
- `[DASHBOARD_6_PANELS_SCREENSHOT]`:

[dashboard_1.png](evidences/dashboard_1.png)

[dashboard_2.png](evidences/dashboard_2.png)

- `[SLO_TABLE]`:

  | SLI | Target | Window | Current Value |
  |---|---:|---|---:|
  | Latency P95 | < 3000ms | 28d | 152 ms |
  | Error Rate | < 2% | 28d | 0.00% |
  | Cost Budget | < $2.5/day | 1d | $0.0608 (latest 30-request batch) |
  | Quality Score Avg | >= 0.75 | 28d | 0.88 |

### 3.3 Alerts & Runbook
- `[ALERT_RULES_SCREENSHOT]`: Alert rules are defined in `config/alert_rules.yaml` and each rule points to a concrete remediation guide in `docs/alerts.md`.

| Alert | Severity | Trigger | Owner | Runbook |
|---|---|---|---|---|
| `high_latency_p95` | P2 | `latency_p95_ms > 3000 for 30m` | `team-oncall` | `docs/alerts.md#1-high-latency-p95` |
| `high_error_rate` | P1 | `error_rate_pct > 2 for 5m` | `team-oncall` | `docs/alerts.md#2-high-error-rate` |
| `cost_budget_spike` | P2 | `hourly_cost_usd > 2x_baseline for 15m` | `finops-owner` | `docs/alerts.md#3-cost-budget-spike` |
| `low_quality_score` | P3 | `quality_score_avg < 0.75 for 60m` | `ml-owner` | `docs/alerts.md#4-low-quality-score` |

- `[SAMPLE_RUNBOOK_LINK]`: [`docs/alerts.md#1-high-latency-p95`](docs/alerts.md#1-high-latency-p95)

---

## 4. Incident Response (Group)
- `[SCENARIO_NAME]`: rag_slow
- `[SYMPTOMS_OBSERVED]`: After enabling the `rag_slow` incident via `POST /incidents/rag_slow/enable`, latency P95 spiked significantly above normal levels (~165 ms baseline). The `/health` endpoint reported `incidents.rag_slow: true`. Structured logs showed increased `latency_ms` values in `response_sent` events. The Langfuse trace waterfall showed the `rag.retrieve` span duration expanding dramatically while the `llm.generate` span remained constant - confirming the slowdown originated in the retrieval layer, not the LLM.
- `[ROOT_CAUSE_PROVED_BY]`: Langfuse trace waterfall comparison: `rag.retrieve` span duration increased from ~5 ms (normal) to ~2000+ ms (incident), while `llm.generate` span remained at ~150 ms. Log lines with `event: "response_sent"` showed `latency_ms` values exceeding the 3000 ms SLO threshold. The `GET /health` endpoint confirmed `rag_slow: true` as the active incident toggle.
- `[FIX_ACTION]`: Called `POST /incidents/rag_slow/disable` to deactivate the injected failure. Verified recovery via `GET /metrics` - latency P95 returned to baseline (~165 ms). Confirmed incident status cleared via `GET /health`.
- `[PREVENTIVE_MEASURE]`: (1) The `high_latency_p95` alert rule (`config/alert_rules.yaml`) triggers automatically when P95 > 3000 ms for 30 minutes, paging the on-call team. (2) The runbook at `docs/alerts.md#1-high-latency-p95` provides step-by-step diagnosis: check Langfuse traces to compare RAG vs LLM span durations, inspect `/health` for active incidents, and apply mitigations (disable incident toggle, reduce corpus size, or truncate queries). (3) Add circuit-breaker timeouts on the RAG retrieval path to fail fast rather than degrade slowly.

---

## 5. Individual Contributions & Evidence

### Nguyễn Huy Tú (2A202600170)
- `[TASKS_COMPLETED]`: Implemented the dashboard UI used for demo/grading, including the visual layout for the live overview header, 6 metric panels, and the load-test appendix shown in `docs/evidences/dashboard_1.png` and `docs/evidences/dashboard_2.png`; ran and validated Langfuse so the team could capture trace waterfalls for `agent.run`, `rag.retrieve`, and `llm.generate`, then use those traces in the report and incident analysis; also implemented PII redaction in the logging pipeline by enabling `scrub_event`, adding recursive scrub for nested log fields (dict/list/tuple), extending `PII_PATTERNS` with `passport` and `address`, and adding tests for email, VN phone, credit card, passport, address, and nested payload redaction. Verified with `.venv` using `pytest` (6 passed) and runtime validation where PII scrubbing passed.
- `[EVIDENCE_LINK]`: [commit 49d7af8](https://github.com/huytu0702/Lab13-Observability_Nhom36/commit/49d7af8cebb3db3980ad7437af8bc968453c7417)

### Phạm Quốc Vương (2A202600419)
- `[TASKS_COMPLETED]`:
  - Implemented correlation ID middleware in `app/middleware.py`: added `clear_contextvars()` to prevent context leakage between requests; generate unique IDs using format `req-{uuid4.hex[:8]}`; extract existing `x-request-id` from request headers or auto-generate; bind `correlation_id` to structlog contextvars for automatic propagation across all log entries.
  - Added response headers `x-request-id` and `x-response-time-ms` for client-side tracking and latency measurement.
  - Implemented log enrichment in `app/main.py` `/chat` endpoint: bind `user_id_hash`, `session_id`, `feature`, `model`, and `env` to structlog contextvars so every downstream log line carries full request context.
  - Enhanced `app/tracing.py` with Langfuse v3 SDK integration: implemented `langfuse_span()` and `langfuse_generation()` context managers for creating hierarchical trace spans; added `update_current_trace()` for trace-level metadata (user, session, tags); implemented `flush()` for graceful shutdown; provided safe no-op fallbacks when SDK is absent.
  - Enhanced `app/agent.py` to propagate `correlation_id` into Langfuse trace metadata and create structured spans for `rag.retrieve` and `llm.generate` pipeline steps.
  - Added `app/main.py` shutdown event to flush pending Langfuse traces.
  - Achieved 100/100 validation score with 30 unique correlation IDs and zero PII leaks.
- `[EVIDENCE_LINK]`: [commit 5609c5a](https://github.com/huytu0702/Lab13-Observability_Nhom36/commit/5609c5a)

### Trương Minh Phước (2A202600330)
- `[TASKS_COMPLETED]`:
  - Refined `config/slo.yaml`: added `group`, `description` fields for each SLI and linked each SLI to its alert rule; targets are `latency_p95_ms < 3000 ms`, `error_rate_pct < 2%`, `daily_cost_usd < $2.50`, `quality_score_avg >= 0.75`.
  - Extended `config/alert_rules.yaml`: tightened latency threshold from 5000 ms to 3000 ms (aligned with SLO); tightened error-rate threshold from 5% to 2% (aligned with SLO); added full `annotations` (summary + description) to all 3 existing rules; added 4th alert rule `low_quality_score` (severity P3, trigger `quality_score_avg < 0.75 for 60m`).
  - Expanded `docs/alerts.md` runbook: enriched all 3 existing runbooks with severity, first-check steps, mitigation actions, and escalation path; added runbook section 4 for `low_quality_score` including RAG doc_count check and over-redaction diagnosis.
  - Built `scripts/check_slo.py`: standalone Python script that fetches live `/metrics` from the running FastAPI app, loads `config/slo.yaml`, evaluates each SLI against its objective, and prints a compliance table (exit code 0 = all pass, 1 = breach). Supports `--url` flag and `--json` output mode.
  - Verified compliance: ran `python scripts/check_slo.py` after 30 live requests - all 4 SLOs passed (P95=152 ms, error_rate=0.00%, cost=$0.0608, quality=0.88). `validate_logs.py` score = 100/100, 0 PII leaks, 30 unique correlation IDs.
- `[EVIDENCE_LINK]`: [commit 5315476](https://github.com/huytu0702/Lab13-Observability_Nhom36/commit/5315476)

### Nguyễn Thành Trung (2A202600451)
- `[TASKS_COMPLETED]`:
  - Rewrote `scripts/load_test.py` into a full load generator: added `--concurrency`, `--repeat`, `--duration`, `--rps`, `--report`, `--no-report` flags; per-request capture of latency, cost, tokens, quality, and correlation_id; aggregate summary printed and persisted to `data/load_report.json` (totals, success/failed, error_rate_pct, latency p50/p95/p99/avg/max, cost total/avg, tokens in/out, quality average, error breakdown).
  - Added `scripts/render_dashboard.py`: fetches live `/metrics`, joins it with `data/load_report.json`, loads `config/slo.yaml` (PyYAML optional, hand-rolled fallback), and renders the 6 required panels into `docs/dashboard.md` with explicit SLO/threshold lines (Latency P50/P95/P99 vs 3000 ms, Traffic, Error Rate vs 2%, Cost vs $2.50/day, Tokens in/out, Quality vs 0.75). Also writes `data/dashboard_snapshot.json` for parser-friendly grading and prints any breaching panels.
  - Expanded `docs/dashboard-spec.md`: documented the 6 panels with their `/metrics` source field, unit, SLO line, and matching alert (cross-linked to Member C's `config/alert_rules.yaml`); added the load-test -> dashboard workflow and an evidence checklist.
  - Verified end-to-end on a live `uvicorn app.main:app --reload`: ran `python scripts/load_test.py --concurrency 5 --repeat 3` (30 requests, all succeeded) followed by `python scripts/render_dashboard.py`. Output saved to `docs/dashboard.md` and `data/dashboard_snapshot.json`. All 6 panels report **OK** against the SLOs from `config/slo.yaml`:
    - Latency server-side P50/P95/P99 = 151 / 152 / 152 ms (SLO P95 < 3000 ms).
    - Wall-clock latency from the load tester P50/P95/P99 = 775.4 / 1230.84 / 1230.84 ms - the gap vs server-side is HTTP/network overhead, a useful demo of why client-side measurement matters.
    - Error rate = 0.00% (SLO < 2%).
    - Cost = $0.0608 total / $0.0020 avg per request (SLO < $2.50/day).
    - Tokens in/out = 1020 / 3850.
    - Quality avg = 0.88 (SLO >= 0.75).
  - Evidence screenshots committed under `docs/evidences/dashboard_1.png` (overview + panels 1-3) and `docs/evidences/dashboard_2.png` (panels 1-6 + load-test appendix).
- `[EVIDENCE_LINK]`: [commit e2dc345](https://github.com/huytu0702/Lab13-Observability_Nhom36/commit/e2dc345)

### Lương Hoàng Anh (2A202600472)
- `[TASKS_COMPLETED]`:
  - Coordinated team report compilation: created initial `docs/blueprint-template.md` structure, collected individual contributions from all members, and merged into the final report document.
  - Filled in Team Metadata (Section 1): group name, repo URL, and all 5 member names with their assigned roles.
  - Completed Group Performance data (Section 2): recorded final validation score (100/100), total trace count (30), and PII leak count (0).
  - Assembled Technical Evidence (Section 3): linked correlation ID and PII redaction screenshots (`docs/evidences/logs.png`), Langfuse trace waterfall screenshot (`docs/evidences/langfuse_2.png`), dashboard panel screenshots, and SLO compliance table with live metric values.
  - Wrote Incident Response analysis (Section 4): documented the `rag_slow` scenario including symptoms observed, root cause identification via Langfuse trace span comparison, fix actions taken, and preventive measures through alert rules and runbooks.
  - Managed Git workflow: resolved merge conflicts between concurrent team edits on `blueprint-template.md`, ensured all member contributions were preserved, and maintained clean commit history.
  - Prepared demo flow documentation: organized the presentation structure covering the observability pipeline from logging -> tracing -> dashboard -> alerting -> incident response.
- `[EVIDENCE_LINK]`: [commit 109c5da](https://github.com/huytu0702/Lab13-Observability_Nhom36/commit/109c5da)

---

## 6. Bonus Items (Optional)
- `[BONUS_COST_OPTIMIZATION]`: The system implements per-request cost estimation using a model-aware pricing formula in `agent.py` (`_estimate_cost` method: $3/M input tokens, $15/M output tokens). Combined with the `/metrics` endpoint and `scripts/check_slo.py`, the team can track cost in real-time and compare against the $2.50/day SLO budget. Current average cost is $0.002/request - well within budget.
- `[BONUS_AUDIT_LOGS]`: Structured JSON logs are persisted to `data/logs.jsonl` via the `JsonlFileProcessor` in `logging_config.py`, creating a durable audit trail separate from console output. Each log entry includes `correlation_id`, `user_id_hash` (PII-safe), `session_id`, `feature`, `model`, timestamp, and event type - suitable for compliance auditing.
- `[BONUS_CUSTOM_METRIC]`: Added `quality_score` as a 4th SLI/SLO metric beyond the standard latency/error/cost trio. The heuristic quality scorer in `agent.py` (`_heuristic_quality`) evaluates response relevance based on document retrieval success, answer length, keyword overlap with the question, and absence of over-redaction. This metric is tracked end-to-end: computed in the agent -> recorded in `/metrics` -> visualized in dashboard Panel 6 -> monitored by the `low_quality_score` alert rule.
