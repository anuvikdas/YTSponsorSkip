#!/usr/bin/env python3
"""Two-request, native-only local Supadata probe. No generated transcription or retries."""

import argparse
import json
import math
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/src"))

from ytsponsorskip.config import Settings  # noqa: E402
from ytsponsorskip.providers.supadata import (  # noqa: E402
    API_ROOT,
    SupadataProbeError,
    SupadataTranscriptProvider,
)

VIDEO_IDS = ("dQw4w9WgXcQ", "Vw1Qrko8oTs")


def safe_value(value, secret):
    """Redact any echoed key before writing response bodies."""
    if isinstance(value, str):
        return value.replace(secret, "[REDACTED]")
    if isinstance(value, list):
        return [safe_value(item, secret) for item in value]
    if isinstance(value, dict):
        return {key: safe_value(item, secret) for key, item in value.items()}
    return value


def account_credits(session, secret):
    """Read plan/credit counters only; a failed read does not hide transcript evidence."""
    try:
        response = session.get(f"{API_ROOT}/me", timeout=5)
        body = response.json()
        return {
            "http_status": response.status_code,
            "plan": safe_value(body.get("plan"), secret) if isinstance(body, dict) else None,
            "max_credits": body.get("maxCredits") if isinstance(body, dict) else None,
            "used_credits": body.get("usedCredits") if isinstance(body, dict) else None,
        }
    except (requests.RequestException, ValueError):
        return {"http_status": None, "plan": None, "max_credits": None, "used_credits": None}


def require_free_credit(account, *, minimum_remaining=1):
    """Fail closed if the account does not clearly have a free native request available."""
    plan = account["plan"]
    maximum = account["max_credits"]
    used = account["used_credits"]
    if (
        account["http_status"] != 200
        or not isinstance(plan, str)
        or not any(word in plan.lower() for word in ("free", "trial"))
        or isinstance(maximum, bool)
        or isinstance(used, bool)
        or not isinstance(maximum, (int, float))
        or not isinstance(used, (int, float))
        or not math.isfinite(maximum)
        or not math.isfinite(used)
        or maximum - used < minimum_remaining
    ):
        raise SystemExit(
            "Supadata free-credit status could not be confirmed; no transcript request was sent."
        )


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/supadata")
    args = parser.parse_args()
    if any((args.output_dir / f"{video_id}.json").exists() for video_id in VIDEO_IDS):
        parser.error("A video result exists; refusing to repeat a credit-bearing request")
    settings = Settings(_env_file=ROOT / ".env")
    if settings.supadata_api_key is None:
        parser.error("SUPADATA_API_KEY is missing from the project-root .env")
    key = settings.supadata_api_key.get_secret_value()
    provider = SupadataTranscriptProvider(key, total_timeout_seconds=30, max_polls=20)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    before = account_credits(provider._session, key)
    require_free_credit(before, minimum_remaining=len(VIDEO_IDS))
    summaries = []
    account_checks = [before]
    for position, video_id in enumerate(VIDEO_IDS):
        if position:
            check = account_credits(provider._session, key)
            account_checks.append(check)
            require_free_credit(check)
        started = monotonic()
        transcript = None
        failure = None
        try:
            outcome = provider.fetch_with_observations(video_id, ("en",))
            transcript = outcome.transcript
            observations = outcome.observations
        except SupadataProbeError as error:
            observations = error.observations
            failure = {"code": error.code.value, "reason": error.public_message}
        elapsed_ms = round((monotonic() - started) * 1000, 3)
        first = transcript.snippets[0] if transcript else None
        last = transcript.snippets[-1] if transcript else None
        summary = {
            "video_id": video_id,
            "http_outcomes": [observation.status_code for observation in observations],
            "result": "usable" if transcript else "unavailable",
            "error": failure,
            "language": transcript.language_code if transcript else None,
            "caption_type": "unknown",
            "usable_snippet_count": len(transcript.snippets) if transcript else 0,
            "timing_valid": transcript is not None,
            "first_cue_seconds": first.start_seconds if first else None,
            "last_cue_start_seconds": last.start_seconds if last else None,
            "last_cue_end_seconds_derived": last.end_seconds if last else None,
            "end_to_end_latency_ms": elapsed_ms,
            "truncation_assessment": (
                "Requires independent duration comparison; last cue alone does not "
                "establish completeness."
                if transcript
                else "No usable transcript to assess."
            ),
        }
        artifact = {
            "schema_version": 1,
            "acquired_at_utc": datetime.now(UTC).isoformat(),
            "request": {"video_id": video_id, "lang": "en", "mode": "native", "text": False},
            "summary": summary,
            "responses": [safe_value(asdict(observation), key) for observation in observations],
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
        with (output_dir / f"{video_id}.json").open("x", encoding="utf-8") as target:
            json.dump(artifact, target, indent=2, allow_nan=False)
            target.write("\n")
        summaries.append(summary)
        print(
            f"{video_id}: {summary['result']}; HTTP {summary['http_outcomes']}; "
            f"cues={summary['usable_snippet_count']}; lang={summary['language']}; "
            f"elapsed_ms={summary['end_to_end_latency_ms']}; "
            f"error={failure['code'] if failure else 'none'}"
        )
    after = account_credits(provider._session, key)
    report = {
        "schema_version": 1,
        "tested_at_utc": datetime.now(UTC).isoformat(),
        "environment": "local",
        "mode": "native",
        "text": False,
        "requested_language": "en",
        "account_before": before,
        "account_checks": account_checks,
        "account_after": after,
        "observed_credit_delta": (
            after["used_credits"] - before["used_credits"]
            if isinstance(before["used_credits"], (int, float))
            and isinstance(after["used_credits"], (int, float))
            else None
        ),
        "videos": summaries,
    }
    with (output_dir / "report.json").open("x", encoding="utf-8") as target:
        json.dump(report, target, indent=2, allow_nan=False)
        target.write("\n")
    print(f"Saved secret-free response records under {output_dir}")


if __name__ == "__main__":
    run()
