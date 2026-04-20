"""check_slo.py — Evaluate SLO compliance from live /metrics endpoint.

Usage:
    python scripts/check_slo.py [--url http://127.0.0.1:8000]

The script fetches the /metrics snapshot produced by app/metrics.py, loads the
SLO targets from config/slo.yaml, and prints a compliance report with a pass/fail
status for every SLI.  Exit code 0 = all SLOs met; 1 = one or more SLOs breached.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx is not installed. Run: pip install httpx")
    sys.exit(2)

try:
    import yaml  # type: ignore
except ImportError:
    # Fallback: parse the simple yaml by hand so we don't require PyYAML
    yaml = None  # type: ignore

BASE_URL_DEFAULT = "http://127.0.0.1:8000"
SLO_CONFIG_PATH = Path("config/slo.yaml")

# ── Minimal YAML parser (key: value only, ignores comments/blank lines) ────────
def _parse_simple_yaml(text: str) -> dict:
    """Parse the flat slo.yaml without requiring PyYAML."""
    result: dict = {}
    current_sli: dict | None = None
    current_sli_name: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#")[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        if indent == 0:
            if ":" in stripped:
                k, _, v = stripped.partition(":")
                result[k.strip()] = v.strip() if v.strip() else {}
        elif indent == 2:
            if stripped.endswith(":"):
                # start of a section (e.g. slis:)
                pass
            elif ":" in stripped:
                k, _, v = stripped.partition(":")
                key = k.strip()
                val = v.strip()
                if val == "":
                    # This is a new SLI block header inside slis
                    current_sli_name = key
                    current_sli = {}
                    if isinstance(result.get("slis"), dict):
                        result["slis"][current_sli_name] = current_sli
                else:
                    # top-level k:v like service, window, group
                    result[key] = val
        elif indent == 4 and current_sli is not None:
            if ":" in stripped:
                k, _, v = stripped.partition(":")
                try:
                    current_sli[k.strip()] = float(v.strip())  # type: ignore[index]
                except ValueError:
                    current_sli[k.strip()] = v.strip()  # type: ignore[index]
    return result


def load_slo_config() -> dict:
    text = SLO_CONFIG_PATH.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    return _parse_simple_yaml(text)


def fetch_metrics(base_url: str) -> dict:
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(f"{base_url}/metrics")
        resp.raise_for_status()
        return resp.json()


def evaluate(metrics: dict, slo_config: dict) -> list[dict]:
    """Return a list of result dicts, one per SLI."""
    slis = slo_config.get("slis", {})
    results = []

    for name, cfg in slis.items():
        objective = float(cfg.get("objective", 0))
        description = cfg.get("description", "")

        # Map SLI name → metrics key
        if name == "latency_p95_ms":
            current = metrics.get("latency_p95", 0.0)
            breached = current > objective
            direction = "max"
        elif name == "error_rate_pct":
            total = metrics.get("traffic", 0)
            errors = sum(metrics.get("error_breakdown", {}).values())
            current = round((errors / total * 100), 2) if total else 0.0
            breached = current > objective
            direction = "max"
        elif name == "daily_cost_usd":
            current = round(metrics.get("total_cost_usd", 0.0), 4)
            breached = current > objective
            direction = "max"
        elif name == "quality_score_avg":
            current = metrics.get("quality_avg", 0.0)
            breached = current < objective
            direction = "min"
        else:
            current = 0.0
            breached = False
            direction = "unknown"

        results.append(
            {
                "sli": name,
                "description": description,
                "objective": objective,
                "direction": direction,
                "current": current,
                "status": "BREACHED [FAIL]" if breached else "OK [PASS]",
                "breached": breached,
            }
        )
    return results


def print_report(metrics: dict, results: list[dict], slo_config: dict) -> None:
    service = slo_config.get("service", "unknown")
    window = slo_config.get("window", "?")
    group = slo_config.get("group", "?")

    print("=" * 60)
    print(f"  SLO Compliance Report — {service}")
    print(f"  Group: {group} | Window: {window}")
    print("=" * 60)
    print(f"  Traffic snapshot : {metrics.get('traffic', 0)} requests")
    print(f"  Total cost (USD) : ${metrics.get('total_cost_usd', 0.0):.4f}")
    print(f"  Tokens in/out    : {metrics.get('tokens_in_total', 0)} / {metrics.get('tokens_out_total', 0)}")
    print("-" * 60)

    all_ok = True
    for r in results:
        direction_sym = "<=" if r["direction"] == "max" else ">="
        print(
            f"  [{r['status']}] {r['sli']}"
            f"\n          Current={r['current']}  Objective={direction_sym}{r['objective']}"
        )
        if r.get("description"):
            print(f"          {r['description']}")
        if r["breached"]:
            all_ok = False
        print()

    print("-" * 60)
    if all_ok:
        print("  [PASS]  All SLOs are within target.")
    else:
        breached = [r["sli"] for r in results if r["breached"]]
        print(f"  [FAIL]  SLO breach detected: {', '.join(breached)}")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check SLO compliance against the live /metrics endpoint.")
    parser.add_argument("--url", default=BASE_URL_DEFAULT, help="Base URL of the running app (default: %(default)s)")
    parser.add_argument("--json", dest="output_json", action="store_true", help="Print results as JSON instead of a table")
    args = parser.parse_args()

    # Load SLO config
    if not SLO_CONFIG_PATH.exists():
        print(f"ERROR: SLO config not found at {SLO_CONFIG_PATH}")
        return 2

    slo_config = load_slo_config()

    # Fetch live metrics
    try:
        metrics = fetch_metrics(args.url)
    except Exception as exc:
        print(f"ERROR: Could not reach {args.url}/metrics — {exc}")
        print("Tip: Start the app first with: uvicorn app.main:app --reload")
        return 2

    results = evaluate(metrics, slo_config)

    if args.output_json:
        print(json.dumps({"metrics": metrics, "slo_results": results}, indent=2))
    else:
        print_report(metrics, results, slo_config)

    return 1 if any(r["breached"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
