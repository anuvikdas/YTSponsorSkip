#!/usr/bin/env python3
"""Collect one distinct native-only development transcript per invocation, at most five total."""

import argparse
import json
import re
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend/src"))
sys.path.insert(0, str(ROOT / "tools"))

from supadata_probe import account_credits, require_free_credit, safe_value  # noqa: E402
from ytsponsorskip.config import Settings  # noqa: E402
from ytsponsorskip.domain import TranscriptAcquisitionError  # noqa: E402
from ytsponsorskip.providers.native_demo import NativeDemoBudget  # noqa: E402
from ytsponsorskip.providers.supadata import (  # noqa: E402
    SupadataProbeError,
    SupadataTranscriptProvider,
)
from ytsponsorskip.trial_budget import TrialBudget  # noqa: E402

from scripts.collect_heldout_transcripts import normalize  # noqa: E402

OUTPUT = ROOT / "results/development-transcripts"
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
MAX_ADDITIONAL_ATTEMPTS = 5


def collect(video_id: str) -> dict:
    if not VIDEO_ID.fullmatch(video_id):
        raise SystemExit("Invalid video ID; no request sent")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    record_path = OUTPUT / f"{video_id}.attempt.json"
    transcript_path = OUTPUT / f"{video_id}.json"
    attempts = list(OUTPUT.glob("*.attempt.json"))
    if record_path.exists() or transcript_path.exists():
        raise SystemExit("This video already has a development attempt or transcript; no retry")
    other_saved = list((ROOT / "data/transcripts").glob(f"*/{video_id}.json"))
    other_saved += list((ROOT / "results/supadata").glob(f"{video_id}.json"))
    if other_saved:
        raise SystemExit("A saved transcript or provider response already exists; no request")
    if len(attempts) >= MAX_ADDITIONAL_ATTEMPTS:
        raise SystemExit("Five additional development attempts already recorded")
    settings = Settings(_env_file=ROOT / ".env")
    if settings.supadata_api_key is None:
        raise SystemExit("SUPADATA_API_KEY is not configured; no request sent")
    secret = settings.supadata_api_key.get_secret_value()
    budget = TrialBudget(
        settings.trial_budget_path,
        limit=settings.trial_attempt_limit,
        max_polls=settings.trial_poll_limit,
    )
    provider = SupadataTranscriptProvider(
        secret,
        total_timeout_seconds=30,
        per_request_timeout_seconds=5,
        poll_interval_seconds=1,
        max_polls=settings.trial_poll_limit,
        trial_budget=budget,
        enforce_free_credits=True,
    )
    before = account_credits(provider._session, secret)
    require_free_credit(before)
    NativeDemoBudget(settings.trial_budget_path, OUTPUT).reserve(video_id)
    acquired_at = datetime.now(UTC).isoformat()
    # Reserve the campaign attempt before network I/O. An interrupted request still counts.
    record_path.write_text(
        json.dumps(
            {"video_id": video_id, "started_at": acquired_at, "status": "started_or_interrupted"},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    started = time.monotonic()
    result = None
    observations = ()
    error = None
    try:
        result = provider.fetch_with_observations(video_id, ("en",))
        observations = result.observations
    except SupadataProbeError as exc:
        observations = exc.observations
        error = {"code": exc.code.value, "message": exc.public_message}
    except TranscriptAcquisitionError as exc:
        error = {"code": exc.code.value, "message": exc.public_message}
    latency_ms = round((time.monotonic() - started) * 1000, 3)
    if result:
        transcript_path.write_text(
            json.dumps(
                normalize(result, acquired_at=acquired_at),
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
    after = account_credits(provider._session, secret)
    record = {
        "video_id": video_id,
        "acquired_at": acquired_at,
        "request": {"lang": "en", "mode": "native", "text": False},
        "result": "usable" if result else "unavailable",
        "http_statuses": [item.status_code for item in observations],
        "language_code": result.transcript.language_code if result else None,
        "caption_type": "unknown",
        "snippet_count": len(result.transcript.snippets) if result else 0,
        "latency_ms": latency_ms,
        "error": error,
        "account_before": before,
        "account_after": after,
        "observed_credit_delta": (
            after["used_credits"] - before["used_credits"]
            if isinstance(before["used_credits"], (int, float))
            and isinstance(after["used_credits"], (int, float))
            else None
        ),
        "responses": [safe_value(asdict(item), secret) for item in observations],
    }
    record_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_id")
    args = parser.parse_args()
    record = collect(args.video_id)
    print(
        f"{record['video_id']}: {record['result']}; HTTP {record['http_statuses']}; "
        f"cues={record['snippet_count']}; language={record['language_code']}; "
        f"latency_ms={record['latency_ms']}; error={record['error']}; "
        f"observed_credit_delta={record['observed_credit_delta']}"
    )


if __name__ == "__main__":
    main()
