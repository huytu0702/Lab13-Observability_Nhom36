from app.dashboard import build_snapshot


def test_build_snapshot_computes_panel_statuses() -> None:
    metrics = {
        "traffic": 10,
        "latency_p50": 120,
        "latency_p95": 180,
        "latency_p99": 220,
        "avg_cost_usd": 0.0015,
        "total_cost_usd": 0.015,
        "tokens_in_total": 500,
        "tokens_out_total": 1200,
        "error_breakdown": {"RuntimeError": 1},
        "quality_avg": 0.88,
    }
    slo = {
        "service": "svc",
        "group": "team",
        "window": "28d",
        "slis": {
            "latency_p95_ms": {"objective": 3000},
            "error_rate_pct": {"objective": 20},
            "daily_cost_usd": {"objective": 2.5},
            "quality_score_avg": {"objective": 0.75},
        },
    }

    snapshot = build_snapshot(metrics, slo=slo, load={"total": 10, "success": 9, "failed": 1})

    assert snapshot["panels"]["latency"]["status"] == "OK"
    assert snapshot["panels"]["error_rate"]["rate_pct"] == 10.0
    assert snapshot["panels"]["quality"]["status"] == "OK"
    assert snapshot["panels"]["traffic"]["load_test_total"] == 10
