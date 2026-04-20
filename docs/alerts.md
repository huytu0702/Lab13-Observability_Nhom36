# Alert Rules and Runbooks

## 1. High latency P95
- **Alert name**: `high_latency_p95`
- **Severity**: P2
- **Trigger**: `latency_p95_ms > 3000 for 30m`
- **Impact**: Tail latency breaches SLO — up to 5 % of users experience slow responses.
- **First checks**:
  1. Open top slow traces in the last 1 h in Langfuse.
  2. Compare **RAG span** duration vs **LLM span** duration.
  3. Run `GET /health` and check `incidents.rag_slow`.
  4. Check `GET /metrics` → `latency_p95` and `latency_p99`.
- **Mitigation**:
  - If `rag_slow` is `true`: call `POST /incidents/rag_slow/disable` or increase RAG timeout.
  - Truncate long queries to reduce embedding + retrieval time.
  - Switch to a lighter retrieval source (smaller corpus).
  - Lower prompt size (reduce `docs` passed to LLM).
- **Escalation**: If not resolved in 60 m, escalate to P1.

---

## 2. High error rate
- **Alert name**: `high_error_rate`
- **Severity**: P1
- **Trigger**: `error_rate_pct > 2 for 5m`
- **Impact**: Users receive HTTP 500 failed responses. Revenue impact within minutes.
- **First checks**:
  1. Run `GET /metrics` → inspect `error_breakdown` for dominant `error_type`.
  2. Group logs by `error_type` field in `data/logs.jsonl`.
  3. Inspect failed traces in Langfuse (filter by `error = true`).
  4. Determine whether failures are LLM, tool, or schema related.
- **Mitigation**:
  - Rollback latest deployment if errors began immediately after release.
  - Disable failing tool: call `POST /incidents/tool_fail/disable`.
  - Retry with fallback model or reduced prompt size.
  - If schema validation failures: check Pydantic model version drift.
- **Escalation**: Immediate P1 — page on-call engineer.

---

## 3. Cost budget spike
- **Alert name**: `cost_budget_spike`
- **Severity**: P2
- **Trigger**: `hourly_cost_usd > 2x_baseline for 15m`
- **Impact**: Burn rate exceeds daily budget of $2.50 if left unchecked.
- **First checks**:
  1. Run `GET /metrics` → compare `avg_cost_usd` and `total_cost_usd`.
  2. Split traces by `feature` and `model` tags in Langfuse.
  3. Compare `tokens_in` / `tokens_out` ratios across features.
  4. Check whether `cost_spike` incident toggle is active: `GET /health`.
- **Mitigation**:
  - Shorten prompts by reducing `docs` context.
  - Route easy / low-complexity requests to a cheaper model tier.
  - Apply prompt caching where repeated system instructions are sent.
  - Disable `cost_spike` incident if it was injected for testing: `POST /incidents/cost_spike/disable`.
- **Escalation**: Notify FinOps owner; set a hard token-rate limit if available.

---

## 4. Low quality score
- **Alert name**: `low_quality_score`
- **Severity**: P3
- **Trigger**: `quality_score_avg < 0.75 for 60m`
- **Impact**: Responses are factually degraded or incorrectly redacted; users may not notice immediately but satisfaction drops.
- **First checks**:
  1. Run `GET /metrics` → inspect `quality_avg`.
  2. Look for answers containing `[REDACTED` — over-aggressive PII scrubbing reduces score.
  3. Check `doc_count` metadata in Langfuse traces; if 0, retrieval is broken.
  4. Compare quality distribution by `feature` tag (qa vs summary).
- **Mitigation**:
  - If `doc_count == 0`: fix RAG retrieval config or corpus path.
  - If `[REDACTED` in answers: tighten PII patterns to avoid over-redaction.
  - If score is low only for one feature: inspect that feature's prompt template.
  - Temporarily increase retrieval `top_k` to improve document coverage.
- **Escalation**: If score stays below 0.60 after mitigation, escalate to ML owner.
