from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "http://127.0.0.1:8000"
QUERIES = Path("data/sample_queries.jsonl")
DEFAULT_REPORT = Path("data/load_report.json")


@dataclass
class RequestResult:
    status: int
    latency_ms: float
    correlation_id: str | None
    feature: str
    cost_usd: float | None
    tokens_in: int | None
    tokens_out: int | None
    quality_score: float | None
    error: str | None = None


@dataclass
class LoadStats:
    started_at: str
    finished_at: str = ""
    total: int = 0
    success: int = 0
    failed: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    costs_usd: list[float] = field(default_factory=list)
    tokens_in: list[int] = field(default_factory=list)
    tokens_out: list[int] = field(default_factory=list)
    quality_scores: list[float] = field(default_factory=list)
    errors: dict[str, int] = field(default_factory=dict)


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def send_request(client: httpx.Client, payload: dict) -> RequestResult:
    feature = payload.get("feature", "unknown")
    start = time.perf_counter()
    try:
        r = client.post(f"{BASE_URL}/chat", json=payload)
        latency = (time.perf_counter() - start) * 1000
        body: dict[str, Any] = {}
        try:
            body = r.json()
        except Exception:
            body = {}
        if r.status_code == 200:
            print(
                f"[{r.status_code}] {body.get('correlation_id')} | {feature} | "
                f"{latency:.1f}ms | ${body.get('cost_usd', 0):.4f}"
            )
            return RequestResult(
                status=r.status_code,
                latency_ms=latency,
                correlation_id=body.get("correlation_id"),
                feature=feature,
                cost_usd=body.get("cost_usd"),
                tokens_in=body.get("tokens_in"),
                tokens_out=body.get("tokens_out"),
                quality_score=body.get("quality_score"),
            )
        err = body.get("detail") or f"http_{r.status_code}"
        print(f"[{r.status_code}] {feature} | {latency:.1f}ms | error={err}")
        return RequestResult(
            status=r.status_code,
            latency_ms=latency,
            correlation_id=body.get("correlation_id"),
            feature=feature,
            cost_usd=None,
            tokens_in=None,
            tokens_out=None,
            quality_score=None,
            error=str(err),
        )
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        print(f"[ERR] {feature} | {latency:.1f}ms | {type(exc).__name__}: {exc}")
        return RequestResult(
            status=0,
            latency_ms=latency,
            correlation_id=None,
            feature=feature,
            cost_usd=None,
            tokens_in=None,
            tokens_out=None,
            quality_score=None,
            error=type(exc).__name__,
        )


def _record(stats: LoadStats, res: RequestResult) -> None:
    stats.total += 1
    stats.latencies_ms.append(res.latency_ms)
    if res.status == 200:
        stats.success += 1
        if res.cost_usd is not None:
            stats.costs_usd.append(res.cost_usd)
        if res.tokens_in is not None:
            stats.tokens_in.append(res.tokens_in)
        if res.tokens_out is not None:
            stats.tokens_out.append(res.tokens_out)
        if res.quality_score is not None:
            stats.quality_scores.append(res.quality_score)
    else:
        stats.failed += 1
        key = res.error or f"http_{res.status}"
        stats.errors[key] = stats.errors.get(key, 0) + 1


def _build_payloads(repeat: int) -> list[dict]:
    lines = [line for line in QUERIES.read_text(encoding="utf-8").splitlines() if line.strip()]
    payloads = [json.loads(line) for line in lines]
    return payloads * max(1, repeat)


def _run_serial(client: httpx.Client, payloads: list[dict], stats: LoadStats, rps: float | None) -> None:
    interval = 1.0 / rps if rps and rps > 0 else 0.0
    for payload in payloads:
        loop_start = time.perf_counter()
        res = send_request(client, payload)
        _record(stats, res)
        if interval:
            sleep_for = interval - (time.perf_counter() - loop_start)
            if sleep_for > 0:
                time.sleep(sleep_for)


def _run_concurrent(client: httpx.Client, payloads: list[dict], stats: LoadStats, concurrency: int) -> None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_request, client, p) for p in payloads]
        for fut in concurrent.futures.as_completed(futures):
            _record(stats, fut.result())


def _run_duration(
    client: httpx.Client,
    payloads: list[dict],
    stats: LoadStats,
    duration: float,
    concurrency: int,
    rps: float | None,
) -> None:
    deadline = time.perf_counter() + duration
    interval = 1.0 / rps if rps and rps > 0 else 0.0
    idx = 0

    if concurrency <= 1:
        while time.perf_counter() < deadline:
            loop_start = time.perf_counter()
            res = send_request(client, payloads[idx % len(payloads)])
            _record(stats, res)
            idx += 1
            if interval:
                sleep_for = interval - (time.perf_counter() - loop_start)
                if sleep_for > 0:
                    time.sleep(sleep_for)
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        in_flight: set[concurrent.futures.Future] = set()
        while time.perf_counter() < deadline:
            while len(in_flight) < concurrency and time.perf_counter() < deadline:
                fut = executor.submit(send_request, client, payloads[idx % len(payloads)])
                in_flight.add(fut)
                idx += 1
                if interval:
                    time.sleep(interval)
            done, in_flight = concurrent.futures.wait(
                in_flight, timeout=0.1, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for fut in done:
                _record(stats, fut.result())
        for fut in concurrent.futures.as_completed(in_flight):
            _record(stats, fut.result())


def _summarize(stats: LoadStats) -> dict:
    error_rate = (stats.failed / stats.total * 100) if stats.total else 0.0
    return {
        "started_at": stats.started_at,
        "finished_at": stats.finished_at,
        "total": stats.total,
        "success": stats.success,
        "failed": stats.failed,
        "error_rate_pct": round(error_rate, 4),
        "latency_ms": {
            "p50": round(_percentile(stats.latencies_ms, 50), 2),
            "p95": round(_percentile(stats.latencies_ms, 95), 2),
            "p99": round(_percentile(stats.latencies_ms, 99), 2),
            "avg": round(statistics.mean(stats.latencies_ms), 2) if stats.latencies_ms else 0.0,
            "max": round(max(stats.latencies_ms), 2) if stats.latencies_ms else 0.0,
        },
        "cost_usd": {
            "total": round(sum(stats.costs_usd), 6),
            "avg": round(statistics.mean(stats.costs_usd), 6) if stats.costs_usd else 0.0,
        },
        "tokens": {
            "in_total": sum(stats.tokens_in),
            "out_total": sum(stats.tokens_out),
        },
        "quality_score_avg": round(statistics.mean(stats.quality_scores), 4) if stats.quality_scores else 0.0,
        "errors": stats.errors,
    }


def _print_summary(summary: dict) -> None:
    print("\n=== Load Test Summary ===")
    print(f"Total      : {summary['total']}  (success={summary['success']}, failed={summary['failed']})")
    print(f"Error rate : {summary['error_rate_pct']}%")
    lat = summary["latency_ms"]
    print(f"Latency ms : p50={lat['p50']}  p95={lat['p95']}  p99={lat['p99']}  avg={lat['avg']}  max={lat['max']}")
    print(f"Cost (USD) : total={summary['cost_usd']['total']}  avg={summary['cost_usd']['avg']}")
    tk = summary["tokens"]
    print(f"Tokens     : in={tk['in_total']}  out={tk['out_total']}")
    print(f"Quality avg: {summary['quality_score_avg']}")
    if summary["errors"]:
        print(f"Errors     : {summary['errors']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate load against the FastAPI agent and report aggregated metrics."
    )
    parser.add_argument("--concurrency", type=int, default=1, help="Number of concurrent workers")
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Repeat the sample query set N times (ignored when --duration is set)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Run sustained load for N seconds (overrides --repeat)",
    )
    parser.add_argument(
        "--rps",
        type=float,
        default=None,
        help="Throttle to approximately this many requests per second",
    )
    parser.add_argument(
        "--report",
        type=str,
        default=str(DEFAULT_REPORT),
        help="Path to write JSON summary report",
    )
    parser.add_argument("--no-report", action="store_true", help="Skip writing the JSON report file")
    args = parser.parse_args()

    payloads = _build_payloads(args.repeat)
    stats = LoadStats(started_at=datetime.now(timezone.utc).isoformat())

    with httpx.Client(timeout=30.0) as client:
        if args.duration > 0:
            _run_duration(client, payloads, stats, args.duration, max(1, args.concurrency), args.rps)
        elif args.concurrency > 1:
            _run_concurrent(client, payloads, stats, args.concurrency)
        else:
            _run_serial(client, payloads, stats, args.rps)

    stats.finished_at = datetime.now(timezone.utc).isoformat()
    summary = _summarize(stats)
    _print_summary(summary)

    if not args.no_report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"\nReport written: {report_path}")


if __name__ == "__main__":
    main()
