# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- [GROUP_NAME]: 
- [REPO_URL]: 
- [MEMBERS]:
  - Member A: Nguyễn Huy Tú (2A202600170) | Role: Logging & PII
  - Member B: Phạm Quốc Vương (2A202600419) | Role: Tracing & Enrichment
  - Member C: [Name] | Role: SLO & Alerts
  - Member D: [Name] | Role: Load Test & Dashboard
  - Member E: [Name] | Role: Demo & Report

---

## 2. Group Performance (Auto-Verified)
- [VALIDATE_LOGS_FINAL_SCORE]: /100
- [TOTAL_TRACES_COUNT]: 
- [PII_LEAKS_FOUND]: 

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: [Path to image]
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: [Path to image]
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: [Path to image]
- [TRACE_WATERFALL_EXPLANATION]: (Briefly explain one interesting span in your trace)

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: [Path to image]
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| Latency P95 | < 3000ms | 28d | |
| Error Rate | < 2% | 28d | |
| Cost Budget | < $2.5/day | 1d | |

### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: [Path to image]
- [SAMPLE_RUNBOOK_LINK]: [docs/alerts.md#L...]

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

### [MEMBER_C_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

### [MEMBER_D_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

### [MEMBER_E_NAME]
- [TASKS_COMPLETED]: 
- [EVIDENCE_LINK]: 

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: (Description + Evidence)
- [BONUS_AUDIT_LOGS]: (Description + Evidence)
- [BONUS_CUSTOM_METRIC]: (Description + Evidence)
