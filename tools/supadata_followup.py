#!/usr/bin/env python3
"""Exactly one budgeted 30-second follow-up for the previously timed-out video."""

import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))

from supadata_probe import account_credits, require_free_credit, safe_value  # noqa: E402
from ytsponsorskip.config import Settings  # noqa: E402
from ytsponsorskip.domain import TranscriptAcquisitionError  # noqa: E402
from ytsponsorskip.providers.supadata import (  # noqa: E402
    SupadataProbeError,
    SupadataTranscriptProvider,
)
from ytsponsorskip.trial_budget import TrialBudget  # noqa: E402

VIDEO_ID = "Vw1Qrko8oTs"
OUTPUT = ROOT / "results/supadata/Vw1Qrko8oTs-followup.json"


def run():
    if OUTPUT.exists():
        raise SystemExit("Follow-up result already exists; no repeated acquisition is permitted.")
    settings = Settings(_env_file=ROOT / ".env")
    if settings.supadata_api_key is None:
        raise SystemExit("SUPADATA_API_KEY is missing; no acquisition was sent.")
    key = settings.supadata_api_key.get_secret_value()
    budget = TrialBudget(
        settings.trial_budget_path,
        limit=settings.trial_attempt_limit,
        max_polls=settings.trial_poll_limit,
    )
    before_budget = budget.snapshot()
    provider = SupadataTranscriptProvider(
        key,
        total_timeout_seconds=30,
        per_request_timeout_seconds=30,
        max_polls=min(5, settings.trial_poll_limit),
        poll_interval_seconds=1,
        trial_budget=budget,
    )
    account_before = account_credits(provider._session, key)
    require_free_credit(account_before)

    started = monotonic()
    transcript, observations, failure = None, (), None
    try:
        result = provider.fetch_with_observations(VIDEO_ID, ("en",))
        transcript, observations = result.transcript, result.observations
    except SupadataProbeError as error:
        observations = error.observations
        failure = {"code": error.code.value, "message": error.public_message}
    except TranscriptAcquisitionError as error:
        failure = {"code": error.code.value, "message": error.public_message}
    elapsed_ms = round((monotonic() - started) * 1000, 3)

    after_budget = budget.snapshot()
    account_after = account_credits(provider._session, key)
    first = transcript.snippets[0] if transcript else None
    last = transcript.snippets[-1] if transcript else None
    summary = {
        "video_id": VIDEO_ID,
        "result": "usable" if transcript else "unavailable",
        "http_outcomes": [entry.status_code for entry in observations],
        "failure_stage": (
            None if transcript else observations[-1].phase if observations else "initial_request"
        ),
        "error": failure,
        "end_to_end_latency_ms": elapsed_ms,
        "polls_reserved": after_budget["polls_used"] - before_budget["polls_used"],
        "language": transcript.language_code if transcript else None,
        "caption_type": "unknown",
        "usable_snippet_count": len(transcript.snippets) if transcript else 0,
        "timing_valid": transcript is not None,
        "first_cue_seconds": first.start_seconds if first else None,
        "last_cue_start_seconds": last.start_seconds if last else None,
        "last_cue_end_seconds_derived": last.end_seconds if last else None,
        "completeness_note": (
            "Compare this last cue with an independent duration or saved source; "
            "cue end alone does not prove completeness."
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "schema_version": 1,
        "tested_at_utc": datetime.now(UTC).isoformat(),
        "request": {"video_id": VIDEO_ID, "mode": "native", "text": False, "lang": "en"},
        "account_before": account_before,
        "account_after": account_after,
        "budget_before": before_budget,
        "budget_after": after_budget,
        "summary": summary,
        "responses": [safe_value(asdict(entry), key) for entry in observations],
        "normalized_transcript": (
            {
                "video_id": transcript.video_id,
                "transcript": {
                    "language": transcript.language,
                    "language_code": transcript.language_code,
                    "caption_type": "unknown",
                    "is_generated": None,
                    "provider": transcript.provider,
                    "provider_version": transcript.provider_version,
                },
                "snippets": [asdict(snippet) for snippet in transcript.snippets],
            }
            if transcript
            else None
        ),
    }
    with OUTPUT.open("x", encoding="utf-8") as target:
        json.dump(artifact, target, indent=2, allow_nan=False)
        target.write("\n")
    print(
        f"{VIDEO_ID}: {summary['result']}; HTTP {summary['http_outcomes']}; "
        f"cues={summary['usable_snippet_count']}; lang={summary['language']}; "
        f"elapsed_ms={elapsed_ms}; polls={summary['polls_reserved']}; "
        f"error={failure['code'] if failure else 'none'}; "
        f"budget_used={after_budget['attempts_used']}"
    )


if __name__ == "__main__":
    run()
