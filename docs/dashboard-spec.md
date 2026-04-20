# Dashboard Spec

Owner: Member D (Load Test & Dashboard).

The dashboard mirrors the Layer-2 view from the lab brief and is rendered
from the live `/metrics` snapshot of the FastAPI app. Use
`scripts/render_dashboard.py` to regenerate `docs/dashboard.md` and the
machine-readable `data/dashboard_snapshot.json` after every load-test burst.

## Quality bar
- Default time range: **1 hour** rolling (in-memory metrics reset per app restart).
- Auto refresh: **15-30 seconds** (Grafana) / re-run `render_dashboard.py` in CLI.
- Every panel shows its **SLO / threshold line** explicitly.
- Units are labeled (ms, %, USD, tokens).
- 6 required panels — never exceed 6-8 on the main layer.

## Required panels

| # | Panel | Source field(s) (`/metrics`) | Unit | SLO line | Owner alert |
|---|---|---|---|---|---|
| 1 | Latency P50 / P95 / P99 | `latency_p50`, `latency_p95`, `latency_p99` | ms | P95 < **3000 ms** | `high_latency_p95` |
| 2 | Traffic (request count) | `traffic` (+ `total` from load_report) | requests | none (capacity reference) | - |
| 3 | Error rate (with breakdown) | derived: `sum(error_breakdown) / traffic`; raw `error_breakdown` | % | < **2%** | `high_error_rate` |
| 4 | Cost over time | `total_cost_usd`, `avg_cost_usd` | USD | daily < **$2.50** | `cost_budget_spike` |
| 5 | Tokens in / out | `tokens_in_total`, `tokens_out_total` | tokens | none (capacity reference) | - |
| 6 | Quality score (heuristic) | `quality_avg` | 0-1 | >= **0.75** | `low_quality_score` |

## Generating the dashboard

```bash
# 1. Start the app
uvicorn app.main:app --reload

# 2. Generate load (writes data/load_report.json)
python scripts/load_test.py --concurrency 5 --repeat 3

# 3. Render the 6-panel dashboard
python scripts/render_dashboard.py
#  -> writes docs/dashboard.md
#  -> writes data/dashboard_snapshot.json
#  -> exits 0; prints "BREACH panels: [...]" if any SLO line is crossed
```

Optional flags: `--url`, `--out`, `--snapshot`, `--json` (stdout snapshot only).

## How load_test.py feeds the dashboard

`scripts/load_test.py` (Member D) drives traffic into `/chat` and persists a
JSON summary at `data/load_report.json`. `render_dashboard.py` reads that file
to enrich Panel 2 (load-test batch size) and the appendix block (per-run P50/
P95/P99, cost, tokens, quality). Useful invocations:

```bash
# Light smoke pass (1x sample queries, sequential)
python scripts/load_test.py

# Stress with parallelism (5 workers, 3x query set)
python scripts/load_test.py --concurrency 5 --repeat 3

# Sustained 60s load at ~5 RPS
python scripts/load_test.py --duration 60 --rps 5 --concurrency 4

# CI-friendly: skip the report file
python scripts/load_test.py --no-report
```

The summary always includes total/success/failed, error rate %, latency P50/
P95/P99/avg/max, cost total/avg, token in/out totals, average quality, and
error-type breakdown.

## SLO crosswalk

The dashboard thresholds come straight from `config/slo.yaml`. If Member C
adjusts an SLI, the dashboard re-renders automatically — no edits needed here.

## Evidence checklist (Member D)

- [ ] Screenshot of `docs/dashboard.md` (or Grafana board) showing all 6 panels with SLO lines.
- [ ] `data/load_report.json` from the most recent run committed alongside the screenshot.
- [ ] `data/dashboard_snapshot.json` for parser-friendly grading.
