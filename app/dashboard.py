from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

SLO_PATH = Path("config/slo.yaml")
LOAD_REPORT_PATH = Path("data/load_report.json")


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_sli: dict[str, Any] | None = None
    for raw in text.splitlines():
        line = raw.split("#")[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0 and ":" in stripped:
            key, _, value = stripped.partition(":")
            result[key.strip()] = value.strip() if value.strip() else {}
        elif indent == 2 and ":" in stripped:
            key, _, value = stripped.partition(":")
            item_key, item_value = key.strip(), value.strip()
            if item_value == "":
                current_sli = {}
                if isinstance(result.get("slis"), dict):
                    result["slis"][item_key] = current_sli
            else:
                result[item_key] = item_value
        elif indent == 4 and current_sli is not None and ":" in stripped:
            key, _, value = stripped.partition(":")
            parsed = value.strip()
            try:
                current_sli[key.strip()] = float(parsed)
            except ValueError:
                current_sli[key.strip()] = parsed
    return result


def load_slo_config() -> dict[str, Any]:
    if not SLO_PATH.exists():
        return {}
    text = SLO_PATH.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return _parse_simple_yaml(text)


def load_report() -> dict[str, Any] | None:
    if not LOAD_REPORT_PATH.exists():
        return None
    try:
        return json.loads(LOAD_REPORT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _status(value: float, threshold: float, *, lower_is_better: bool = True) -> str:
    if lower_is_better:
        return "OK" if value <= threshold else "BREACH"
    return "OK" if value >= threshold else "BREACH"


def _percent_of_threshold(value: float, threshold: float) -> float:
    if threshold <= 0:
        return 0.0
    return max(0.0, min(100.0, (value / threshold) * 100))


def build_snapshot(metrics: dict[str, Any], slo: dict[str, Any] | None = None, load: dict[str, Any] | None = None) -> dict[str, Any]:
    slo = slo or load_slo_config()
    load = load if load is not None else load_report()
    slis = slo.get("slis", {})

    p95_target = float(slis.get("latency_p95_ms", {}).get("objective", 3000))
    err_target = float(slis.get("error_rate_pct", {}).get("objective", 2))
    cost_target = float(slis.get("daily_cost_usd", {}).get("objective", 2.5))
    quality_target = float(slis.get("quality_score_avg", {}).get("objective", 0.75))

    traffic = int(metrics.get("traffic", 0))
    errors = metrics.get("error_breakdown", {}) or {}
    error_count = sum(errors.values())
    error_rate_pct = round((error_count / traffic * 100), 4) if traffic else 0.0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "service": slo.get("service", "day13-observability-lab"),
        "group": slo.get("group", "Nhom36"),
        "slo_window": slo.get("window", "28d"),
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
                "threshold": p95_target,
                "status": _status(metrics.get("latency_p95", 0.0), p95_target),
                "ratio_pct": _percent_of_threshold(float(metrics.get("latency_p95", 0.0)), p95_target),
            },
            "traffic": {
                "requests": traffic,
                "load_test_total": (load or {}).get("total"),
                "success": (load or {}).get("success"),
                "failed": (load or {}).get("failed"),
            },
            "error_rate": {
                "rate_pct": error_rate_pct,
                "threshold": err_target,
                "breakdown": errors,
                "status": _status(error_rate_pct, err_target),
                "ratio_pct": _percent_of_threshold(error_rate_pct, err_target),
            },
            "cost": {
                "total_usd": metrics.get("total_cost_usd", 0.0),
                "avg_usd": metrics.get("avg_cost_usd", 0.0),
                "threshold": cost_target,
                "status": _status(metrics.get("total_cost_usd", 0.0), cost_target),
                "ratio_pct": _percent_of_threshold(float(metrics.get("total_cost_usd", 0.0)), cost_target),
            },
            "tokens": {
                "in_total": metrics.get("tokens_in_total", 0),
                "out_total": metrics.get("tokens_out_total", 0),
            },
            "quality": {
                "avg": metrics.get("quality_avg", 0.0),
                "threshold": quality_target,
                "status": _status(metrics.get("quality_avg", 0.0), quality_target, lower_is_better=False),
                "ratio_pct": max(0.0, min(100.0, float(metrics.get("quality_avg", 0.0)) * 100)),
            },
        },
        "load_report": load,
    }


def render_dashboard_html(snapshot: dict[str, Any]) -> str:
    panels = snapshot["panels"]
    latency = panels["latency"]
    traffic = panels["traffic"]
    error_rate = panels["error_rate"]
    cost = panels["cost"]
    tokens = panels["tokens"]
    quality = panels["quality"]
    load = snapshot.get("load_report") or {}

    def chip(status: str) -> str:
        css = "good" if status == "OK" else "bad"
        return f'<span class="chip {css}">{status}</span>'

    def meter(value_pct: float) -> str:
        return (
            '<div class="meter">'
            f'<div class="meter-fill" style="width:{value_pct:.1f}%"></div>'
            "</div>"
        )

    error_rows = ""
    breakdown = error_rate["breakdown"]
    if breakdown:
        error_rows = "".join(
            f"<tr><td>{name}</td><td>{count}</td></tr>"
            for name, count in sorted(breakdown.items(), key=lambda item: (-item[1], item[0]))
        )
    else:
        error_rows = '<tr><td colspan="2">No errors recorded</td></tr>'

    appendix = ""
    if load:
        latency_stats = load.get("latency_ms", {})
        cost_stats = load.get("cost_usd", {})
        token_stats = load.get("tokens", {})
        appendix = f"""
        <section class="appendix">
          <div class="section-kicker">Appendix</div>
          <h2>Last load-test batch</h2>
          <div class="appendix-grid">
            <div>
              <div class="label">Window</div>
              <div class="value small">{load.get("started_at", "-")} -> {load.get("finished_at", "-")}</div>
            </div>
            <div>
              <div class="label">Total</div>
              <div class="value">{load.get("total", 0)}</div>
            </div>
            <div>
              <div class="label">Success / Failed</div>
              <div class="value">{load.get("success", 0)} / {load.get("failed", 0)}</div>
            </div>
            <div>
              <div class="label">Client P95 latency</div>
              <div class="value">{latency_stats.get("p95", 0)} ms</div>
            </div>
            <div>
              <div class="label">Load cost total</div>
              <div class="value">${cost_stats.get("total", 0):.4f}</div>
            </div>
            <div>
              <div class="label">Load quality avg</div>
              <div class="value">{load.get("quality_score_avg", 0):.2f}</div>
            </div>
            <div>
              <div class="label">Tokens in / out</div>
              <div class="value">{token_stats.get("in_total", 0)} / {token_stats.get("out_total", 0)}</div>
            </div>
            <div>
              <div class="label">Error rate</div>
              <div class="value">{load.get("error_rate_pct", 0):.2f}%</div>
            </div>
          </div>
        </section>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Day 13 Dashboard</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --panel: rgba(255,255,255,0.76);
      --ink: #1d2a21;
      --muted: #56645d;
      --line: rgba(29,42,33,0.12);
      --good: #1d6b4f;
      --bad: #a33f26;
      --accent: #c47f2c;
      --accent-soft: #f4d7a9;
      --shadow: 0 20px 50px rgba(43, 52, 45, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(196,127,44,0.20), transparent 28%),
        radial-gradient(circle at top right, rgba(29,107,79,0.16), transparent 24%),
        linear-gradient(180deg, #f7f1e9 0%, var(--bg) 100%);
      font-family: "Trebuchet MS", "Segoe UI", sans-serif;
    }}
    .shell {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.4fr 0.8fr;
      gap: 18px;
      align-items: stretch;
      margin-bottom: 22px;
    }}
    .hero-card, .meta-card, .card, .appendix {{
      background: var(--panel);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255,255,255,0.65);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .hero-card {{
      padding: 28px;
    }}
    .meta-card {{
      padding: 24px;
      display: grid;
      gap: 14px;
      align-content: start;
    }}
    .eyebrow {{
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    h1, h2 {{
      font-family: Georgia, "Times New Roman", serif;
      margin: 0;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}
    h1 {{
      font-size: clamp(2.2rem, 5vw, 4.8rem);
      line-height: 0.98;
      max-width: 10ch;
    }}
    .hero-copy {{
      margin-top: 14px;
      max-width: 62ch;
      line-height: 1.55;
      color: var(--muted);
      font-size: 15px;
    }}
    .hero-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 22px;
    }}
    .button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      padding: 0 16px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      text-decoration: none;
      font-weight: 600;
    }}
    .button.primary {{
      background: var(--ink);
      color: #fff;
      border-color: transparent;
    }}
    .meta-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }}
    .meta-item {{
      padding: 14px;
      border-radius: 18px;
      background: rgba(255,255,255,0.7);
      border: 1px solid var(--line);
    }}
    .label {{
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    .value {{
      font-size: 28px;
      font-weight: 700;
      line-height: 1.1;
    }}
    .value.small {{
      font-size: 14px;
      line-height: 1.5;
      word-break: break-word;
    }}
    .status-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 18px;
    }}
    .card {{
      grid-column: span 4;
      padding: 22px;
      position: relative;
      overflow: hidden;
      min-height: 250px;
    }}
    .card::after {{
      content: "";
      position: absolute;
      right: -42px;
      top: -42px;
      width: 120px;
      height: 120px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(196,127,44,0.20), rgba(196,127,44,0));
    }}
    .card-top {{
      display: flex;
      justify-content: space-between;
      align-items: start;
      gap: 12px;
      margin-bottom: 18px;
    }}
    .section-kicker {{
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 11px;
      margin-bottom: 6px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .chip.good {{
      background: rgba(29,107,79,0.12);
      color: var(--good);
    }}
    .chip.bad {{
      background: rgba(163,63,38,0.12);
      color: var(--bad);
    }}
    .metrics-row {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }}
    .mini {{
      padding: 12px;
      border-radius: 16px;
      background: rgba(255,255,255,0.72);
      border: 1px solid var(--line);
    }}
    .mini strong {{
      display: block;
      font-size: 24px;
      margin-top: 6px;
    }}
    .meter {{
      height: 12px;
      width: 100%;
      background: rgba(29,42,33,0.08);
      border-radius: 999px;
      overflow: hidden;
      margin: 10px 0 8px;
    }}
    .meter-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--accent), #ddb36d 65%, #f0d7ad 100%);
      border-radius: inherit;
    }}
    .subtext {{
      color: var(--muted);
      line-height: 1.55;
      font-size: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      font-size: 14px;
    }}
    td, th {{
      text-align: left;
      padding: 10px 0;
      border-bottom: 1px solid var(--line);
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-weight: 700;
    }}
    .appendix {{
      margin-top: 18px;
      padding: 24px;
    }}
    .appendix-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-top: 16px;
    }}
    .footnote {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 1080px) {{
      .hero {{
        grid-template-columns: 1fr;
      }}
      .card {{
        grid-column: span 6;
      }}
      .appendix-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
    }}
    @media (max-width: 720px) {{
      .shell {{
        padding: 18px 14px 28px;
      }}
      .meta-grid,
      .metrics-row,
      .appendix-grid {{
        grid-template-columns: 1fr;
      }}
      .card {{
        grid-column: span 12;
        min-height: 0;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <article class="hero-card">
        <div class="eyebrow">Day 13 Observability Lab</div>
        <h1>Live dashboard for demo and grading</h1>
        <p class="hero-copy">
          This view is rendered directly from the running FastAPI app. It combines the current in-memory metrics,
          the SLO thresholds from <code>config/slo.yaml</code>, and the latest load-test report when available.
        </p>
        <div class="hero-actions">
          <a class="button primary" href="/dashboard">Refresh view</a>
          <a class="button" href="/dashboard/snapshot">Open JSON snapshot</a>
          <a class="button" href="/metrics">Open raw metrics</a>
        </div>
      </article>
      <aside class="meta-card">
        <div class="status-row">
          <div>
            <div class="label">Service</div>
            <div class="value">{snapshot["service"]}</div>
          </div>
          {chip("OK")}
        </div>
        <div class="meta-grid">
          <div class="meta-item">
            <div class="label">Group</div>
            <div class="value">{snapshot["group"]}</div>
          </div>
          <div class="meta-item">
            <div class="label">SLO window</div>
            <div class="value">{snapshot["slo_window"]}</div>
          </div>
          <div class="meta-item">
            <div class="label">Rendered</div>
            <div class="value small">{snapshot["generated_at"]}</div>
          </div>
          <div class="meta-item">
            <div class="label">Auto refresh</div>
            <div class="value">15s</div>
          </div>
        </div>
      </aside>
    </section>

    <section class="grid">
      <article class="card">
        <div class="card-top">
          <div>
            <div class="section-kicker">Panel 1</div>
            <h2>Latency</h2>
          </div>
          {chip(latency["status"])}
        </div>
        <div class="metrics-row">
          <div class="mini"><span class="label">P50</span><strong>{latency["p50"]:.0f} ms</strong></div>
          <div class="mini"><span class="label">P95</span><strong>{latency["p95"]:.0f} ms</strong></div>
          <div class="mini"><span class="label">P99</span><strong>{latency["p99"]:.0f} ms</strong></div>
        </div>
        {meter(latency["ratio_pct"])}
        <div class="subtext">SLO line: P95 must stay below <strong>{latency["threshold"]:.0f} ms</strong>.</div>
      </article>

      <article class="card">
        <div class="card-top">
          <div>
            <div class="section-kicker">Panel 2</div>
            <h2>Traffic</h2>
          </div>
          <span class="chip good">Live</span>
        </div>
        <div class="metrics-row">
          <div class="mini"><span class="label">Requests</span><strong>{traffic["requests"]}</strong></div>
          <div class="mini"><span class="label">Load batch</span><strong>{traffic["load_test_total"] or 0}</strong></div>
          <div class="mini"><span class="label">Failed</span><strong>{traffic["failed"] or 0}</strong></div>
        </div>
        <div class="subtext">Capacity reference panel. Use this with load-test appendix to explain what the app handled in the current process window.</div>
      </article>

      <article class="card">
        <div class="card-top">
          <div>
            <div class="section-kicker">Panel 3</div>
            <h2>Error rate</h2>
          </div>
          {chip(error_rate["status"])}
        </div>
        <div class="metrics-row">
          <div class="mini"><span class="label">Rate</span><strong>{error_rate["rate_pct"]:.2f}%</strong></div>
          <div class="mini"><span class="label">Threshold</span><strong>{error_rate["threshold"]:.2f}%</strong></div>
          <div class="mini"><span class="label">Error types</span><strong>{len(breakdown)}</strong></div>
        </div>
        {meter(error_rate["ratio_pct"])}
        <table>
          <thead><tr><th>Error type</th><th>Count</th></tr></thead>
          <tbody>{error_rows}</tbody>
        </table>
      </article>

      <article class="card">
        <div class="card-top">
          <div>
            <div class="section-kicker">Panel 4</div>
            <h2>Cost</h2>
          </div>
          {chip(cost["status"])}
        </div>
        <div class="metrics-row">
          <div class="mini"><span class="label">Total</span><strong>${cost["total_usd"]:.4f}</strong></div>
          <div class="mini"><span class="label">Avg / req</span><strong>${cost["avg_usd"]:.4f}</strong></div>
          <div class="mini"><span class="label">Budget</span><strong>${cost["threshold"]:.2f}</strong></div>
        </div>
        {meter(cost["ratio_pct"])}
        <div class="subtext">Daily budget SLO. This is the easiest place to narrate a before/after optimization story for bonus points.</div>
      </article>

      <article class="card">
        <div class="card-top">
          <div>
            <div class="section-kicker">Panel 5</div>
            <h2>Tokens</h2>
          </div>
          <span class="chip good">Reference</span>
        </div>
        <div class="metrics-row">
          <div class="mini"><span class="label">Tokens in</span><strong>{tokens["in_total"]}</strong></div>
          <div class="mini"><span class="label">Tokens out</span><strong>{tokens["out_total"]}</strong></div>
          <div class="mini"><span class="label">Out / In</span><strong>{(tokens["out_total"] / tokens["in_total"] if tokens["in_total"] else 0):.2f}x</strong></div>
        </div>
        <div class="subtext">Capacity reference panel for model usage. Pair it with cost and quality to explain trade-offs clearly during the demo.</div>
      </article>

      <article class="card">
        <div class="card-top">
          <div>
            <div class="section-kicker">Panel 6</div>
            <h2>Quality</h2>
          </div>
          {chip(quality["status"])}
        </div>
        <div class="metrics-row">
          <div class="mini"><span class="label">Average</span><strong>{quality["avg"]:.2f}</strong></div>
          <div class="mini"><span class="label">Floor</span><strong>{quality["threshold"]:.2f}</strong></div>
          <div class="mini"><span class="label">Headroom</span><strong>{max(0.0, quality["avg"] - quality["threshold"]):.2f}</strong></div>
        </div>
        {meter(quality["ratio_pct"])}
        <div class="subtext">SLO line: quality average must stay above <strong>{quality["threshold"]:.2f}</strong>. Useful for explaining retrieval failures and over-redaction.</div>
      </article>
    </section>

    {appendix}

    <p class="footnote">
      This page auto-refreshes every 15 seconds so the numbers stay current while you demo.
    </p>
  </main>
  <script>
    setTimeout(() => window.location.reload(), 15000);
  </script>
</body>
</html>
"""
