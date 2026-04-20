"""Render a 6-panel observability dashboard from /metrics + load_report.json.

Member D deliverable. Fetches the live snapshot exposed by the FastAPI app at
``GET /metrics``, joins it with the latest load-test summary if present, and
writes a Markdown dashboard with explicit SLO / threshold lines per panel:

  1. Latency P50 / P95 / P99
  2. Traffic (request count)
  3. Error rate (with breakdown)
  4. Cost over time (total + average)
  5. Tokens in / out
  6. Quality score average

Usage::

    python scripts/render_dashboard.py
    python scripts/render_dashboard.py --url http://127.0.0.1:8000 --out docs/dashboard.md
    python scripts/render_dashboard.py --json   # machine-readable snapshot
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

DEFAULT_URL = "http://127.0.0.1:8000"
DEFAULT_OUT = Path("docs/dashboard.md")
DEFAULT_SNAPSHOT = Path("data/dashboard_snapshot.json")
SLO_PATH = Path("config/slo.yaml")
LOAD_REPORT = Path("data/load_report.json")


def _fetch_metrics(base_url: str) -> dict:
    r = httpx.get(f"{base_url.rstrip('/')}/metrics", timeout=10.0)
    r.raise_for_status()
    return r.json()


def _parse_simple_yaml(text: str) -> dict:
    """Minimal YAML reader for config/slo.yaml when PyYAML is unavailable."""
    result: dict = {}
    current_sli: dict | None = None
    for raw in text.splitlines():
        line = raw.split("#")[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0 and ":" in stripped:
            k, _, v = stripped.partition(":")
            result[k.strip()] = v.strip() if v.strip() else {}
        elif indent == 2 and ":" in stripped:
            k, _, v = stripped.partition(":")
            key, val = k.strip(), v.strip()
            if val == "":
                current_sli = {}
                if isinstance(result.get("slis"), dict):
                    result["slis"][key] = current_sli
            else:
                result[key] = val
        elif indent == 4 and current_sli is not None and ":" in stripped:
            k, _, v = stripped.partition(":")
            try:
                current_sli[k.strip()] = float(v.strip())
            except ValueError:
                current_sli[k.strip()] = v.strip()
    return result


def _load_slo() -> dict:
    if not SLO_PATH.exists():
        return {}
    text = SLO_PATH.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return _parse_simple_yaml(text)


def _load_load_report() -> dict | None:
    if not LOAD_REPORT.exists():
        return None
    try:
        return json.loads(LOAD_REPORT.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _status(value: float, threshold: float, *, lower_is_better: bool = True) -> str:
    if lower_is_better:
        return "OK" if value <= threshold else "BREACH"
    return "OK" if value >= threshold else "BREACH"


def _bar(value: float, threshold: float, width: int = 20) -> str:
    if threshold <= 0:
        return ""
    ratio = max(0.0, min(1.5, value / threshold))
    filled = int(round(min(1.0, ratio) * width))
    bar = "#" * filled + "-" * (width - filled)
    over = "!" if ratio > 1.0 else " "
    return f"[{bar}]{over}"


def build_snapshot(metrics: dict, slo: dict, load_report: dict | None) -> dict:
    slis = (slo or {}).get("slis", {})
    p95_target = float(slis.get("latency_p95_ms", {}).get("objective", 3000))
    err_target = float(slis.get("error_rate_pct", {}).get("objective", 2))
    cost_target = float(slis.get("daily_cost_usd", {}).get("objective", 2.5))
    quality_target = float(slis.get("quality_score_avg", {}).get("objective", 0.75))

    traffic = int(metrics.get("traffic", 0))
    errors = metrics.get("error_breakdown", {}) or {}
    error_count = sum(errors.values())
    error_rate_pct = (error_count / traffic * 100) if traffic else 0.0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "service": (slo or {}).get("service", "day13-observability-lab"),
        "group": (slo or {}).get("group", "Nhom36"),
        "slo_window": (slo or {}).get("window", "28d"),
        "thresholds": {
            "latency_p95_ms": p95_target,
            "error_rate_pct": err_target,
            "daily_cost_usd": cost_target,
            "quality_score_avg": quality_target,
        },
        "panels": {
            "latency": {
                "p50": metrics.get("latency_p50", 0.0),
                "p95": metrics.get("latency_p95", 0.0),
                "p99": metrics.get("latency_p99", 0.0),
                "threshold_p95_ms": p95_target,
                "status": _status(metrics.get("latency_p95", 0.0), p95_target),
            },
            "traffic": {
                "requests": traffic,
                "load_test_total": (load_report or {}).get("total"),
            },
            "error_rate": {
                "rate_pct": round(error_rate_pct, 4),
                "threshold_pct": err_target,
                "breakdown": errors,
                "status": _status(error_rate_pct, err_target),
            },
            "cost": {
                "total_usd": metrics.get("total_cost_usd", 0.0),
                "avg_usd": metrics.get("avg_cost_usd", 0.0),
                "threshold_daily_usd": cost_target,
                "status": _status(metrics.get("total_cost_usd", 0.0), cost_target),
            },
            "tokens": {
                "in_total": metrics.get("tokens_in_total", 0),
                "out_total": metrics.get("tokens_out_total", 0),
            },
            "quality": {
                "avg": metrics.get("quality_avg", 0.0),
                "threshold": quality_target,
                "status": _status(metrics.get("quality_avg", 0.0), quality_target, lower_is_better=False),
            },
        },
        "load_report": load_report,
    }


def render_markdown(snapshot: dict) -> str:
    p = snapshot["panels"]
    th = snapshot["thresholds"]
    lat = p["latency"]
    err = p["error_rate"]
    cost = p["cost"]
    tok = p["tokens"]
    qual = p["quality"]
    lr = snapshot.get("load_report")

    lines: list[str] = []
    lines.append("# Day 13 Observability Dashboard")
    lines.append("")
    lines.append(f"- Service : `{snapshot['service']}`")
    lines.append(f"- Group   : `{snapshot['group']}`")
    lines.append(f"- Window  : `{snapshot['slo_window']}`")
    lines.append(f"- Rendered: `{snapshot['generated_at']}`")
    lines.append("")
    lines.append("> Auto-generated by `scripts/render_dashboard.py` (Member D).")
    lines.append("> Auto-refresh: re-run after each load-test burst (15-30s recommended in Grafana).")
    lines.append("")

    lines.append("## Panel 1 - Latency P50 / P95 / P99 (ms)")
    lines.append("")
    lines.append("| Percentile | Value (ms) | SLO Threshold | Status |")
    lines.append("|---|---:|---:|:---:|")
    lines.append(f"| P50 | {lat['p50']:.1f} | - | - |")
    lines.append(f"| **P95** | **{lat['p95']:.1f}** | < {th['latency_p95_ms']:.0f} | **{lat['status']}** |")
    lines.append(f"| P99 | {lat['p99']:.1f} | - | - |")
    lines.append("")
    lines.append(f"`{_bar(lat['p95'], th['latency_p95_ms'])}` P95 vs SLO line")
    lines.append("")

    lines.append("## Panel 2 - Traffic (request count)")
    lines.append("")
    lines.append(f"- Total requests served (in-memory window): **{p['traffic']['requests']}**")
    if p["traffic"]["load_test_total"] is not None:
        lines.append(f"- Last load-test batch: **{p['traffic']['load_test_total']}** requests")
    lines.append("")

    lines.append("## Panel 3 - Error Rate")
    lines.append("")
    lines.append(f"- Rate: **{err['rate_pct']:.2f}%**  (SLO: < {th['error_rate_pct']}%) -> **{err['status']}**")
    lines.append(f"- `{_bar(err['rate_pct'], th['error_rate_pct'])}` vs SLO line")
    lines.append("")
    lines.append("Breakdown by error type:")
    if err["breakdown"]:
        lines.append("")
        lines.append("| Error Type | Count |")
        lines.append("|---|---:|")
        for k, v in sorted(err["breakdown"].items(), key=lambda kv: -kv[1]):
            lines.append(f"| `{k}` | {v} |")
    else:
        lines.append("")
        lines.append("_No errors recorded._")
    lines.append("")

    lines.append("## Panel 4 - Cost over time (USD)")
    lines.append("")
    lines.append(f"- Total spend: **${cost['total_usd']:.4f}**")
    lines.append(f"- Avg per request: **${cost['avg_usd']:.6f}**")
    lines.append(f"- Daily SLO budget: **${th['daily_cost_usd']:.2f}** -> **{cost['status']}**")
    lines.append(f"- `{_bar(cost['total_usd'], th['daily_cost_usd'])}` total vs daily budget")
    lines.append("")

    lines.append("## Panel 5 - Tokens in / out")
    lines.append("")
    lines.append("| Metric | Total |")
    lines.append("|---|---:|")
    lines.append(f"| Tokens in  | {tok['in_total']} |")
    lines.append(f"| Tokens out | {tok['out_total']} |")
    lines.append("")

    lines.append("## Panel 6 - Quality score (heuristic)")
    lines.append("")
    lines.append(f"- Average quality: **{qual['avg']:.3f}**  (SLO: >= {th['quality_score_avg']}) -> **{qual['status']}**")
    if th["quality_score_avg"] > 0:
        ratio = min(1.0, qual["avg"] / 1.0)
        filled = int(round(ratio * 20))
        threshold_pos = int(round(th["quality_score_avg"] * 20))
        bar = list("-" * 20)
        for i in range(filled):
            bar[i] = "#"
        if 0 <= threshold_pos < 20:
            bar[threshold_pos] = "|"
        lines.append(f"- `[{''.join(bar)}]` (| = SLO floor)")
    lines.append("")

    if lr:
        lines.append("---")
        lines.append("")
        lines.append("## Appendix - Last load-test summary")
        lines.append("")
        lines.append(f"- Window: `{lr.get('started_at')}` -> `{lr.get('finished_at')}`")
        lines.append(f"- Total: {lr.get('total')}  (success={lr.get('success')}, failed={lr.get('failed')})")
        lines.append(f"- Error rate: {lr.get('error_rate_pct')}%")
        lat_s = lr.get("latency_ms", {})
        lines.append(
            f"- Latency ms: p50={lat_s.get('p50')}  p95={lat_s.get('p95')}  p99={lat_s.get('p99')}  "
            f"avg={lat_s.get('avg')}  max={lat_s.get('max')}"
        )
        cost_s = lr.get("cost_usd", {})
        lines.append(f"- Cost USD: total={cost_s.get('total')}  avg={cost_s.get('avg')}")
        tok_s = lr.get("tokens", {})
        lines.append(f"- Tokens: in={tok_s.get('in_total')}  out={tok_s.get('out_total')}")
        lines.append(f"- Quality avg: {lr.get('quality_score_avg')}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the 6-panel observability dashboard from /metrics.")
    parser.add_argument("--url", default=DEFAULT_URL, help="Base URL of the running FastAPI app")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Markdown output path")
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT), help="JSON snapshot output path")
    parser.add_argument("--json", action="store_true", help="Print JSON snapshot to stdout instead of writing files")
    args = parser.parse_args()

    metrics = _fetch_metrics(args.url)
    slo = _load_slo()
    load_report = _load_load_report()
    snapshot = build_snapshot(metrics, slo, load_report)

    if args.json:
        print(json.dumps(snapshot, indent=2))
        return

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_markdown(snapshot), encoding="utf-8")

    snap_path = Path(args.snapshot)
    snap_path.parent.mkdir(parents=True, exist_ok=True)
    snap_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    print(f"Dashboard written: {out_path}")
    print(f"Snapshot written : {snap_path}")
    breaches = [k for k, v in snapshot["panels"].items() if isinstance(v, dict) and v.get("status") == "BREACH"]
    if breaches:
        print(f"BREACH panels    : {breaches}")
    else:
        print("All SLO panels   : OK")


if __name__ == "__main__":
    main()
