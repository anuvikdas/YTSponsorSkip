#!/usr/bin/env python3
"""Exercise the local demo API on two saved inputs and one preselected native input."""

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/demo-smoke-2026-10-22.json"
SELECTION = ROOT / "data/experiments/unfamiliar-demo-selection-2026-10-22.json"


def main():
    if OUTPUT.exists():
        raise SystemExit(
            "Smoke-test record exists; inspect/reuse it rather than repeating acquisitions"
        )
    origin = "http://127.0.0.1:8000"
    status = requests.get(origin + "/api/v1/demo-status", timeout=5).json()
    if status["detector_variant"] != "contextual_v1":
        raise SystemExit("Contextual backend is not active")
    selected = json.loads(SELECTION.read_text())
    report = {
        "started_at_utc": datetime.now(UTC).isoformat(),
        "status_before": status,
        "unfamiliar_selected_before_output": selected["video_id"],
        "requests": [],
    }
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    for video_id, source in [
        ("I9hJ_Rux9y0", "saved"),
        ("U3aXWizDbQ4", "saved"),
        (selected["video_id"], "supadata"),
    ]:
        started = time.perf_counter()
        try:
            response = requests.get(
                f"{origin}/api/v1/detections/{video_id}",
                params={
                    "mode": "conservative",
                    "source": source,
                    "expected_detector_version": status["detector_version"],
                },
                headers={"X-Request-ID": "demo-smoke-" + video_id},
                timeout=35,
            )
            row = {
                "video_id": video_id,
                "source": source,
                "http_status": response.status_code,
                "response": response.json(),
            }
        except (requests.RequestException, ValueError) as error:
            row = {
                "video_id": video_id,
                "source": source,
                "http_status": None,
                "error_type": type(error).__name__,
                "no_retry": True,
            }
        row["client_latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
        report["requests"].append(row)
        OUTPUT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        print(video_id, row["http_status"], row.get("response", {}).get("intervals"), flush=True)
    report["status_after"] = requests.get(origin + "/api/v1/demo-status", timeout=5).json()
    OUTPUT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("Remaining native attempts:", report["status_after"]["native_attempts_remaining"])


if __name__ == "__main__":
    main()
