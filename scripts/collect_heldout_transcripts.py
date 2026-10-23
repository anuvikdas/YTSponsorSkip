#!/usr/bin/env python3
"""One-pass, native-only held-out collection; never retries a reserved video ID."""

import csv
import json
import sqlite3
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
from ytsponsorskip.detection_service import validate_transcript  # noqa: E402
from ytsponsorskip.domain import TranscriptAcquisitionError  # noqa: E402
from ytsponsorskip.providers.supadata import (  # noqa: E402
    SupadataProbeError,
    SupadataTranscriptProvider,
)
from ytsponsorskip.trial_budget import TrialBudget  # noqa: E402

from scripts.evaluate_detector import usable_transcript  # noqa: E402

LABELS = ROOT / "data/validation/revised-2026-10-19/videos.csv"
TRANSCRIPTS = ROOT / "data/transcripts/held_out"
RECORDS = ROOT / "results/heldout-acquisition"
MAX_NEW_ATTEMPTS = 8


def heldout_ids() -> list[str]:
    with LABELS.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    ids = [
        row["video_id"]
        for row in rows
        if row["split"] == "held_out" and row["review_status"] == "reviewed"
    ]
    if len(ids) != 8 or len(set(ids)) != 8:
        raise SystemExit("Expected exactly eight distinct fully reviewed held-out videos")
    return ids


def prior_attempt_ids(budget: TrialBudget) -> set[str]:
    with sqlite3.connect(budget.path) as connection:
        return {
            row[0]
            for row in connection.execute(
                "SELECT video_id FROM attempts WHERE source = 'supadata-native'"
            )
        }


def saved_is_valid(path: Path, video_id: str) -> bool:
    if not path.exists():
        return False
    try:
        transcript = usable_transcript(json.loads(path.read_text(encoding="utf-8")))
        if transcript is None:
            return False
        validate_transcript(transcript, video_id)
    except (OSError, ValueError, TranscriptAcquisitionError):
        return False
    return True


def normalize(result, *, acquired_at: str) -> dict:
    transcript = result.transcript
    return {
        "schema_version": 1,
        "status": "ready",
        "video_id": transcript.video_id,
        "acquired_at": acquired_at,
        "source": {
            "library": "supadata-native",
            "version": transcript.provider_version,
            "request": {"lang": "en", "mode": "native", "text": False},
            "credentials_used": "backend_api_key_only",
            "manual_sponsor_annotations_used_as_input": False,
        },
        "transcript": {
            "language": transcript.language,
            "language_code": transcript.language_code,
            "caption_type": "unknown",
            "is_generated": None,
            "provider": transcript.provider,
            "provider_version": transcript.provider_version,
        },
        "timing": {
            "source_unit": "milliseconds",
            "normalized_unit": "seconds",
            "duration_available": True,
            "duration_is_exact_promotion_boundary": False,
        },
        "completeness": {
            "snippet_count": len(transcript.snippets),
            "first_start_seconds": transcript.snippets[0].start_seconds,
            "last_start_seconds": transcript.snippets[-1].start_seconds,
            "independently_verified": False,
            "note": (
                "Provider cue list was nonempty; video duration/truncation requires "
                "independent verification."
            ),
        },
        "snippets": [asdict(snippet) for snippet in transcript.snippets],
    }


def run() -> None:
    ids = heldout_ids()
    settings = Settings(_env_file=ROOT / ".env")
    if settings.supadata_api_key is None:
        raise SystemExit("No backend Supadata key is configured; no acquisition attempted")
    key = settings.supadata_api_key.get_secret_value()
    budget = TrialBudget(
        settings.trial_budget_path,
        limit=settings.trial_attempt_limit,
        max_polls=settings.trial_poll_limit,
    )
    provider = SupadataTranscriptProvider(
        key,
        total_timeout_seconds=30,
        per_request_timeout_seconds=30,
        poll_interval_seconds=1,
        max_polls=settings.trial_poll_limit,
        trial_budget=budget,
        enforce_free_credits=True,
    )
    account = account_credits(provider._session, key)
    require_free_credit(account)
    print(
        f"Free-credit preflight: {account['used_credits']}/{account['max_credits']} "
        f"used; ledger: {budget.snapshot()['attempts_used']}/50"
    )
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    RECORDS.mkdir(parents=True, exist_ok=True)
    new_attempts = 0
    prior = prior_attempt_ids(budget)
    for video_id in ids:
        path = TRANSCRIPTS / f"{video_id}.json"
        record_path = RECORDS / f"{video_id}.json"
        if saved_is_valid(path, video_id):
            print(f"{video_id}: saved transcript present; no request")
            continue
        if path.exists():
            print(f"{video_id}: invalid saved file; refusing to overwrite it")
            continue
        if video_id in prior or record_path.exists():
            print(f"{video_id}: prior attempt found; no retry")
            continue
        if new_attempts >= MAX_NEW_ATTEMPTS:
            break
        account = account_credits(provider._session, key)
        try:
            require_free_credit(account)
        except SystemExit:
            print("Free-credit preflight failed; stopping all acquisition")
            break
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
        elapsed_ms = round((time.monotonic() - started) * 1000, 3)
        # A provider-side Free preflight may fail before the ledger reservation.
        reserved = video_id in prior_attempt_ids(budget)
        if reserved:
            new_attempts += 1
            prior.add(video_id)
        acquired_at = datetime.now(UTC).isoformat()
        record = {
            "video_id": video_id,
            "acquired_at": acquired_at,
            "request": {"lang": "en", "mode": "native", "text": False},
            "reserved_attempt": reserved,
            "http_statuses": [item.status_code for item in observations],
            "latency_ms": elapsed_ms,
            "result": "usable" if result else "unavailable",
            "error": error,
            "responses": [safe_value(asdict(item), key) for item in observations],
        }
        with record_path.open("x", encoding="utf-8") as target:
            json.dump(record, target, ensure_ascii=False, indent=2, allow_nan=False)
            target.write("\n")
        if result:
            with path.open("x", encoding="utf-8") as target:
                json.dump(
                    normalize(result, acquired_at=acquired_at),
                    target,
                    ensure_ascii=False,
                    indent=2,
                    allow_nan=False,
                )
                target.write("\n")
        cue_count = len(result.transcript.snippets) if result else 0
        error_code = error["code"] if error else "none"
        print(
            f"{video_id}: {record['result']}; HTTP {record['http_statuses']}; "
            f"cues={cue_count}; latency_ms={elapsed_ms}; error={error_code}"
        )
        account_error = any(
            "limit-exceeded" in json.dumps(item.body) or "unauthorized" in json.dumps(item.body)
            for item in observations
        )
        if error and (
            not reserved
            or any(status in (401, 429) for status in record["http_statuses"])
            or account_error
            or error["code"] in ("TRIAL_BUDGET_EXHAUSTED", "TRIAL_BUDGET_UNAVAILABLE")
        ):
            print("Account-wide or local-budget failure; stopping all acquisition")
            break
        if new_attempts < MAX_NEW_ATTEMPTS:
            time.sleep(2)
    account_after = account_credits(provider._session, key)
    print(
        f"New held-out attempts: {new_attempts}/{MAX_NEW_ATTEMPTS}; "
        f"ledger: {budget.snapshot()['attempts_used']}/50; observed credits used: "
        f"{account_after['used_credits']}/{account_after['max_credits']}"
    )


if __name__ == "__main__":
    run()
