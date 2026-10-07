from ytsponsorskip.detector import (
    DetectedInterval,
    PromotionDetector,
    RulesWindowClassifier,
    Sensitivity,
    TranscriptWindow,
    build_windows,
    validate_intervals,
)
from ytsponsorskip.domain import Transcript, TranscriptSnippet


def transcript(*snippets: tuple[str, float, float], video_id: str = "synthetic") -> Transcript:
    return Transcript(
        video_id=video_id,
        language="English",
        language_code="en",
        is_generated=False,
        snippets=tuple(
            TranscriptSnippet(
                index=index,
                text=text,
                start_seconds=start,
                duration_seconds=duration,
            )
            for index, (text, start, duration) in enumerate(snippets)
        ),
        provider="synthetic-test-fixture",
        provider_version="1",
    )


def test_build_windows_overlap_and_preserve_snippet_identities() -> None:
    source = transcript(
        ("one", 0, 5),
        ("two", 12, 5),
        ("three", 26, 5),
        ("four", 40, 5),
    )

    windows = build_windows(source, window_seconds=30, overlap_seconds=15)

    assert windows[0].snippet_indices == (0, 1, 2)
    assert windows[1].snippet_indices == (1, 2, 3)
    assert windows[0].window_id != windows[1].window_id


def test_third_party_pitch_becomes_a_refined_conservative_interval() -> None:
    source = transcript(
        ("Before we continue,", 98, 2),
        ("thanks to Acme for sponsoring this video.", 100, 4),
        ("Their service keeps your files organized.", 104, 4),
        ("Use code SAVE20 for 20% off; the link is in the description.", 108, 4),
        ("Now back to the camera test.", 112, 3),
    )

    result = PromotionDetector().detect(source, Sensitivity.CONSERVATIVE)

    assert len(result.intervals) == 1
    assert result.intervals[0].start_seconds == 98
    assert result.intervals[0].end_seconds == 112
    assert {"disclosure", "cta", "offer"} <= set(result.intervals[0].evidence)


def test_creator_owned_pitch_requires_commercial_action() -> None:
    detector = PromotionDetector()
    discussion = transcript(
        ("I built an app to understand how rendering works.", 0, 5),
        ("Here is the architecture and source code.", 5, 5),
    )
    pitch = transcript(
        ("I launched my course for working developers.", 0, 5),
        ("Sign up today and use my code for a discount.", 5, 5),
    )

    assert detector.detect(discussion).intervals == ()
    assert len(detector.detect(pitch).intervals) == 1


def test_product_review_language_alone_does_not_trigger() -> None:
    source = transcript(
        ("This is my review of the Acme camera.", 0, 4),
        ("The autofocus is fast but the battery is weak.", 4, 4),
        ("Let us compare it with the older model.", 8, 4),
    )

    assert PromotionDetector().detect(source, Sensitivity.AGGRESSIVE).intervals == ()


def test_aggressive_policy_still_requires_promotion_context() -> None:
    classifier = RulesWindowClassifier()
    affiliate_transition = classifier.score(
        TranscriptWindow(
            window_id=0,
            start_seconds=0,
            end_seconds=5,
            snippet_indices=(0,),
            text="But first, some of these are affiliate links.",
        )
    )
    brand_only = classifier.score(
        TranscriptWindow(
            window_id=1,
            start_seconds=0,
            end_seconds=5,
            snippet_indices=(0,),
            text="The Acme camera uses a larger sensor.",
        )
    )

    assert not classifier.qualifies(affiliate_transition, Sensitivity.CONSERVATIVE)
    assert classifier.qualifies(affiliate_transition, Sensitivity.AGGRESSIVE)
    assert not classifier.qualifies(brand_only, Sensitivity.AGGRESSIVE)


def test_validate_intervals_rejects_invalid_and_merges_overlap() -> None:
    intervals = validate_intervals(
        [
            DetectedInterval(10, 20, 4, ("disclosure",), (1,)),
            DetectedInterval(18, 25, 6, ("cta",), (2,)),
            DetectedInterval(30, 30, 9, ("offer",), (3,)),
        ]
    )

    assert intervals == (DetectedInterval(10, 25, 6, ("cta", "disclosure"), (1, 2)),)
