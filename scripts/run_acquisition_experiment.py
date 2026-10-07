#!/usr/bin/env python3
import argparse
import csv
import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * fraction), len(ordered) - 1)
    return round(ordered[index], 2)


def latency_summary(rows: list[dict[str, Any]]) -> dict[str, float | int | None]:
    latencies = [float(row["end_to_end_latency_ms"]) for row in rows]
    return {
        "count": len(latencies),
        "median_ms": round(statistics.median(latencies), 2) if latencies else None,
        "p90_ms": percentile(latencies, 0.90),
        "max_ms": round(max(latencies), 2) if latencies else None,
    }


def fetch(base_url: str, video_id: str, timeout: float) -> dict[str, Any]:
    quoted_id = urllib.parse.quote(video_id, safe="")
    url = f"{base_url.rstrip('/')}/api/v1/transcripts/{quoted_id}?languages=en"
    request_id = f"experiment-{time.time_ns()}"
    request = urllib.request.Request(url, headers={"X-Request-ID": request_id})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_body = response.read()
            status_code = response.status
    except urllib.error.HTTPError as error:
        raw_body = error.read()
        status_code = error.code
    except (urllib.error.URLError, TimeoutError) as error:
        return {
            "success": False,
            "status_code": None,
            "end_to_end_latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "failure_code": "ENDPOINT_UNREACHABLE",
            "failure_detail": str(error.reason if hasattr(error, "reason") else error),
        }

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    try:
        body = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {
            "success": False,
            "status_code": status_code,
            "end_to_end_latency_ms": elapsed_ms,
            "failure_code": "ENDPOINT_INVALID_RESPONSE",
            "failure_detail": "The endpoint did not return the JSON API contract.",
        }

    if status_code != 200:
        error = body.get("error", {})
        return {
            "success": False,
            "status_code": status_code,
            "end_to_end_latency_ms": elapsed_ms,
            "failure_code": error.get("code", "UNKNOWN_HTTP_ERROR"),
            "failure_detail": error.get("message"),
        }

    transcript = body["transcript"]
    timing = body["timing"]
    provider_latency = body["provider_latency_ms"]
    return {
        "success": True,
        "status_code": status_code,
        "end_to_end_latency_ms": elapsed_ms,
        "provider_latency_ms": round(provider_latency, 2) if provider_latency is not None else None,
        "cache_hit": body["cache_hit"],
        "coalesced": body["coalesced"],
        "language_code": transcript["language_code"],
        "caption_type": "generated" if transcript["is_generated"] else "manual",
        "provider_version": transcript["provider_version"],
        "snippets": body["snippets"],
        **timing,
    }


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def summarize(rows: list[dict[str, Any]], corpus_size: int) -> dict[str, Any]:
    eligible = [row for row in rows if row["expected_outcome"] == "success"]
    negatives = [row for row in rows if row["expected_outcome"] == "expected_failure"]
    successful = [row for row in rows if row["success"]]
    failed = [row for row in rows if not row["success"]]
    unexpected_failures = [row for row in eligible if not row["success"]]
    unexpected_successes = [row for row in negatives if row["success"]]

    by_caption_type: dict[str, Any] = {}
    for caption_type in ("manual", "generated"):
        group = [row for row in eligible if row["expected_caption_type"] == caption_type]
        successes = [
            row for row in group if row["success"] and row.get("caption_type") == caption_type
        ]
        by_caption_type[caption_type] = {
            "attempts": len(group),
            "successes": len(successes),
            "success_rate": rate(len(successes), len(group)),
        }

    cached = [row for row in successful if row.get("cache_hit")]
    uncached = [row for row in successful if not row.get("cache_hit")]
    first_request = rows[:1]
    warm_uncached = [row for row in uncached if row["request_number"] != 1]
    provider_latencies = [
        float(row["provider_latency_ms"])
        for row in uncached
        if row.get("provider_latency_ms") is not None
    ]
    overlap_counts = [int(row["overlapping_snippet_count"]) for row in successful]
    start_gaps = [
        float(row["median_start_gap_seconds"])
        for row in successful
        if row.get("median_start_gap_seconds") is not None
    ]
    snippet_durations = [
        float(row["median_snippet_duration_seconds"])
        for row in successful
        if row.get("median_snippet_duration_seconds") is not None
    ]

    return {
        "corpus_videos": corpus_size,
        "attempts": len(rows),
        "eligible_caption_attempts": len(eligible),
        "eligible_caption_successes": sum(row["success"] for row in eligible),
        "eligible_caption_success_rate": rate(
            sum(row["success"] for row in eligible), len(eligible)
        ),
        "caption_type_results": by_caption_type,
        "expected_failure_attempts": len(negatives),
        "expected_failures_observed": sum(not row["success"] for row in negatives),
        "unexpected_failure_count": len(unexpected_failures),
        "unexpected_failure_codes": dict(
            Counter(str(row.get("failure_code")) for row in unexpected_failures)
        ),
        "unexpected_success_count": len(unexpected_successes),
        "successful_request_latency": latency_summary(successful),
        "failed_request_latency": latency_summary(failed),
        "first_request_latency": latency_summary(first_request),
        "warm_uncached_success_latency": latency_summary(warm_uncached),
        "uncached_success_latency": latency_summary(uncached),
        "cached_success_latency": latency_summary(cached),
        "uncached_provider_latency_ms": {
            "count": len(provider_latencies),
            "median": round(statistics.median(provider_latencies), 2)
            if provider_latencies
            else None,
            "p90": percentile(provider_latencies, 0.90),
            "max": round(max(provider_latencies), 2) if provider_latencies else None,
        },
        "failure_codes": dict(Counter(str(row.get("failure_code")) for row in failed)),
        "timing_granularity": {
            "median_start_gap_seconds_across_transcripts": round(statistics.median(start_gaps), 3)
            if start_gaps
            else None,
            "min_median_start_gap_seconds": round(min(start_gaps), 3) if start_gaps else None,
            "max_median_start_gap_seconds": round(max(start_gaps), 3) if start_gaps else None,
            "median_snippet_duration_seconds_across_transcripts": round(
                statistics.median(snippet_durations), 3
            )
            if snippet_durations
            else None,
            "transcripts_with_overlaps": sum(count > 0 for count in overlap_counts),
            "max_overlapping_snippet_count": max(overlap_counts) if overlap_counts else None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--corpus", type=Path, default=Path("data/acquisition_corpus.csv"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--environment", required=True)
    args = parser.parse_args()

    with args.corpus.open(newline="", encoding="utf-8") as source:
        corpus = list(csv.DictReader(source))

    rows: list[dict[str, Any]] = []
    request_number = 0
    for attempt in range(1, args.attempts + 1):
        for item in corpus:
            request_number += 1
            result = fetch(args.base_url, item["video_id"], args.timeout)
            rows.append(
                {
                    "request_number": request_number,
                    "attempt": attempt,
                    **item,
                    **result,
                }
            )
            if args.delay_seconds:
                time.sleep(args.delay_seconds)

    report = {
        "environment": args.environment,
        "base_url": args.base_url,
        "run_at": datetime.now(UTC).isoformat(),
        "method": {
            "attempts_per_video": args.attempts,
            "delay_seconds": args.delay_seconds,
            "corpus_file": str(args.corpus),
        },
        "summary": summarize(rows, len(corpus)),
        "results": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
