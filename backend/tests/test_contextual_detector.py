"""Experimental contextual candidate tests; the frozen baseline is unchanged."""

from ytsponsorskip.contextual_detector import ContextualPromotionDetector
from ytsponsorskip.detector import PromotionDetector, Sensitivity
from ytsponsorskip.domain import Transcript, TranscriptSnippet


def transcript(*items):
    return Transcript(
        video_id="synthetic001",
        language="English",
        language_code="en",
        is_generated=None,
        snippets=tuple(
            TranscriptSnippet(index, text, start, duration)
            for index, (text, start, duration) in enumerate(items)
        ),
        provider="test-fixture",
        provider_version="1",
    )


def test_explicit_same_brand_intro_bridges_to_later_offer():
    source = transcript(
        ("The lesson is ending.", 0, 3),
        ("And now with today's sponsor: Acme.", 100, 3),
        ("Acme helps you practice every day.", 108, 5),
        ("There are many useful lessons.", 119, 5),
        ("You can learn at your own pace.", 132, 5),
        ("Try Acme for free for 30 days.", 155, 5),
        ("Use code SAVE20 for 20% off; visit acme.org, link in description.", 161, 15),
    )
    baseline = PromotionDetector().detect(source, Sensitivity.CONSERVATIVE)
    changed = ContextualPromotionDetector().detect(source, Sensitivity.CONSERVATIVE)

    assert baseline.intervals and baseline.intervals[0].start_seconds > 100
    assert changed.intervals[0].start_seconds == 100
    assert "sponsor_intro_continuity" in changed.intervals[0].evidence


def test_unmatched_brand_or_return_to_content_does_not_bridge():
    source = transcript(
        ("Today's sponsor: Acme.", 100, 3),
        ("Now back to the lesson.", 110, 3),
        ("The other company offers a free trial.", 150, 5),
        ("Visit other.org and use the link below.", 156, 5),
    )
    baseline = PromotionDetector().detect(source)
    changed = ContextualPromotionDetector().detect(source)
    assert changed.intervals == baseline.intervals


def test_owned_shop_ask_has_creation_to_shop_boundaries():
    source = transcript(
        ("This is how friendship works.", 0, 5),
        ("We created a few things to share with friends.", 20, 5),
        ("The pins and posters fit together.", 25, 5),
        ("Or browse all the things we made for you.", 30, 5),
        ("Getting something from our shop supports us.", 35, 5),
    )
    assert PromotionDetector().detect(source).intervals == ()
    changed = ContextualPromotionDetector().detect(source)
    assert [(item.start_seconds, item.end_seconds) for item in changed.intervals] == [(20, 40)]


def test_product_review_and_incidental_patreon_mention_remain_negative():
    source = transcript(
        ("I chose the espresso machines for their availability.", 0, 5),
        ("Several models were suggested by my Patreon group.", 5, 5),
        ("Now let's compare the shots and basket sizes.", 10, 5),
    )
    assert ContextualPromotionDetector().detect(source).intervals == ()
