# Day 13 Observability Lab Report

> [!IMPORTANT]
> This report is designed to be parsed by an automated grading assistant. All tags (e.g., `[GROUP_NAME]`) have been preserved and bolded for visibility.

## 1. Team Metadata
- **[GROUP_NAME]**: [Nhom 36]
- **[REPO_URL]**: https://github.com/huytu0702/Lab13-Observability_Nhom36.git
- **[MEMBERS]**:
  - Member A: [Nguyễn Huy Tú] | Role: Logging & PII
  - Member B: [Phạm Quốc Vương] | Role: Tracing & Enrichment
  - Member C: [Trương Minh Phước] | Role: SLO & Alerts
  - Member D: [Nguyễn Thành Trung] | Role: Load Test & Dashboard
  - Member E: [Lương Hoàng Anh] | Role: Demo & Report

---

## 2. Group Performance (Auto-Verified)
- **[VALIDATE_LOGS_FINAL_SCORE]**: 100/100
- **[TOTAL_TRACES_COUNT]**: 30
- **[PII_LEAKS_FOUND]**: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- **[EVIDENCE_CORRELATION_ID_SCREENSHOT]** & **[EVIDENCE_PII_REDACTION_SCREENSHOT]**: [logs.png](https://github.com/huytu0702/Lab13-Observability_Nhom36/blob/main/docs/evidences/logs.png?raw=true)
- **[EVIDENCE_TRACE_WATERFALL_SCREENSHOT]**: [langfuse_2.png](https://github.com/huytu0702/Lab13-Observability_Nhom36/blob/main/docs/evidences/langfuse_2.png?raw=true)
- **[TRACE_WATERFALL_EXPLANATION]**: The `llm.generate` span inside `agent.run` captures the full lifecycle: model name (`claude-sonnet-4-5`), token counts, and cost ($0.002). The hierarchical structure allows quick root-cause differentiation between RAG and LLM bottlenecks.

### 3.2 Dashboard & SLOs
- **[DASHBOARD_6_PANELS_SCREENSHOT]**: [dashboard-panels-1.png](file:///d:/Labs/Lab13-Observability_Nhom36/docs/evidence/dashboard-panels-1.png), [dashboard-panels-2.png](file:///d:/Labs/Lab13-Observability_Nhom36/docs/evidence/dashboard-panels-2.png)
- **[SLO_TABLE]**:

| SLI | Target | Window | Current Value | Status |
|---|---:|---|---:|:---:|
| Latency P95 | < 3000ms | 28d | 165 ms | ✅ |
| Error Rate | < 2% | 28d | 0.0% | ✅ |
| Cost Budget | < $2.5/day | 1d | $0.0631 | ✅ |
| Quality Score | >= 0.75 | 28d | 0.88 | ✅ |

### 3.3 Alerts & Runbook
- **[ALERT_RULES_SCREENSHOT]**: Defined 4 rules in `alert_rules.yaml`: `high_latency_p95` (P2), `high_error_rate` (P1), `cost_budget_spike` (P2), and `low_quality_score` (P3) with detailed annotations and ownership.
- **[SAMPLE_RUNBOOK_LINK]**: [Runbook: High Latency](file:///d:/Labs/Lab13-Observability_Nhom36/docs/alerts.md#1-high-latency-p95)

---

## 4. Incident Response (Group)
- **[SCENARIO_NAME]**: `rag_slow`
- **[SYMPTOMS_OBSERVED]**: P95 latency spiked significantly above baseline. `/health` confirmed `rag_slow: true`. Langfuse waterfall showed `rag.retrieve` duration expanding while `llm.generate` remained stable.
- **[ROOT_CAUSE_PROVED_BY]**: Trace comparison showed RAG span increasing from ~5ms to 2000ms+. Confirmed by health check and logs.
- **[FIX_ACTION]**: Deactivated incident via `POST /incidents/rag_slow/disable`. Verified P95 return to ~165ms.
- **[PREVENTIVE_MEASURE]**: Automated P2 alert rule and documented runbook for manual mitigation; recommended implementing circuit breakers on the RAG path.

---

## 5. Individual Contributions & Evidence

### Nguyễn Huy Tú (2A202600170)
- **[TASKS_COMPLETED]**: Implemented PII redaction pipeline with recursive scrubbing for nested fields. Extended patterns for passport/address and verified with `pytest` and runtime tests.
- **[EVIDENCE_LINK]**: [Commit: 49d7af8](https://github.com/huytu0702/Lab13-Observability_Nhom36/commit/49d7af8cebb3db3980ad7437af8bc968453c7417)

### Phạm Quốc Vương (Member B)
- **[TASKS_COMPLETED]**: Implemented Correlation ID middleware and log enrichment (user_id_hash, session, etc.). Integrated Langfuse v3 SDK with hierarchical tracing and automated flushing.
- **[EVIDENCE_LINK]**: [Commit: 5609c5a](https://github.com/huytu0702/Lab13-Observability_Nhom36/commit/5609c5a)

### Trương Minh Phước (2A202600330)
- **[TASKS_COMPLETED]**: Defined SLOs and Alert Rules with full runbooks. Built `scripts/check_slo.py` to automate compliance verification against live metrics.
- **[EVIDENCE_LINK]**: [Commit: 5315476](https://github.com/huytu0702/Lab13-Observability_Nhom36/commit/5315476)

### Nguyễn Thành Trung (2A202600451)
- **[TASKS_COMPLETED]**: Built comprehensive load testing generator and dashboard renderer. Documented panel specs and verified 6-panel compliance with SLO lines.
- **[EVIDENCE_LINK]**: [Commit: e2dc345](https://github.com/huytu0702/Lab13-Observability_Nhom36/commit/e2dc345)

### Lương Hoàng Anh (Member E)
- **[TASKS_COMPLETED]**: Coordinated report compilation, managed git merge conflicts, and documented incident response analysis. Prepared demo structure and project finalization.
- **[EVIDENCE_LINK]**: [Commit: 109c5da](https://github.com/huytu0702/Lab13-Observability_Nhom36/commit/109c5da)

---

## 6. Bonus Items (Optional)
- **[BONUS_COST_OPTIMIZATION]**: Real-time cost tracking against $2.50 daily budget.
- **[BONUS_AUDIT_LOGS]**: Persistent JSON audit trail in `data/logs.jsonl`.
- **[BONUS_CUSTOM_METRIC]**: Heuristic quality score SLI tracked end-to-end, visualized in dashboard Panel 6, and monitored by the `low_quality_score` alert rule.
