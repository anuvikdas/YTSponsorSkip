"""Experimental explicit-pitch context rescue; frozen rules remain in detector.py."""

import re
from dataclasses import replace

from ytsponsorskip.detector import (
    CandidateSegment,
    DetectedInterval,
    DetectionResult,
    PromotionDetector,
    RulesWindowClassifier,
    Sensitivity,
    TranscriptWindow,
    WindowScore,
    assemble_candidates,
    build_windows,
    refine_boundaries,
    validate_intervals,
)
from ytsponsorskip.domain import Transcript

SPONSOR_INTRO = re.compile(
    r"\b(?:today'?s sponsor|this video'?s sponsor|sponsored by|brought to you by)"
    r"\s*:?\s*([A-Za-z][A-Za-z0-9-]{2,})\b",
    re.IGNORECASE,
)
RETURN_TO_CONTENT = re.compile(
    r"\b(?:now back to|back to (?:the|our|what)|let'?s get back to|anyway,? back to)\b",
    re.IGNORECASE,
)
MAX_INTRO_TO_CANDIDATE_SECONDS = 90.0
OWNED_SHOP = re.compile(r"\b(?:my|our)\s+(?:shop|store)\b", re.IGNORECASE)
SHOP_ACTION = re.compile(r"\b(?:buy|browse|order|pick up|get(?:ting)?)\b", re.IGNORECASE)
CREATOR_ACTION = re.compile(
    r"\b(?:we(?:'ve| have)?\s+(?:created|made|built)|"
    r"(?:support|supports|supporting)\s+(?:us|me|the channel))\b",
    re.IGNORECASE,
)


class ContextualRulesWindowClassifier(RulesWindowClassifier):
    """Anchor an explicit creator-owned shop ask without requiring a formal coupon/URL."""

    def score(self, window: TranscriptWindow) -> WindowScore:
        baseline = super().score(window)
        text = window.text.replace("’", "'")
        if OWNED_SHOP.search(text) and SHOP_ACTION.search(text) and CREATOR_ACTION.search(text):
            return WindowScore(
                score=baseline.score + 3,
                evidence=baseline.evidence + ("owned_shop_action",),
            )
        return baseline

    def qualifies(self, score: WindowScore, sensitivity: Sensitivity) -> bool:
        return "owned_shop_action" in score.evidence or super().qualifies(score, sensitivity)


def bridge_sponsor_introductions(
    transcript: Transcript,
    candidates: tuple[CandidateSegment, ...],
) -> tuple[CandidateSegment, ...]:
    """Add original cues after an explicit same-brand intro to a later sales candidate.

    This operates solely on transcript text/timing and pre-existing rule candidates. It does
    not use annotations and never extends across an explicit return-to-content marker.
    """
    cues = tuple(transcript.snippets)
    by_id = {cue.index: cue for cue in cues}
    positions = {cue.index: position for position, cue in enumerate(cues)}
    output = []
    for candidate in candidates:
        candidate_positions = [positions[index] for index in candidate.snippet_indices]
        first_position = min(candidate_positions)
        first_start = cues[first_position].start_seconds
        # Require a later actionable offer. A standalone sponsor disclosure never becomes
        # a new candidate, which avoids skipping short deferred-sponsor announcements.
        if not set(candidate.evidence) & {"offer", "cta", "url"}:
            output.append(candidate)
            continue
        candidate_text = " ".join(by_id[index].text for index in candidate.snippet_indices)
        chosen_position = None
        for position in range(first_position - 1, -1, -1):
            cue = cues[position]
            if first_start - cue.start_seconds > MAX_INTRO_TO_CANDIDATE_SECONDS:
                break
            match = SPONSOR_INTRO.search(cue.text.replace("\n", " "))
            if not match:
                continue
            brand = match.group(1)
            if not re.search(rf"\b{re.escape(brand)}\b", candidate_text, re.IGNORECASE):
                continue
            gap_text = " ".join(item.text for item in cues[position + 1 : first_position])
            if RETURN_TO_CONTENT.search(gap_text):
                continue
            chosen_position = position
            break
        if chosen_position is None:
            output.append(candidate)
            continue
        bridged_indices = tuple(
            sorted(
                set(candidate.snippet_indices)
                | {cue.index for cue in cues[chosen_position:first_position]}
            )
        )
        output.append(
            replace(
                candidate,
                snippet_indices=bridged_indices,
                evidence=tuple(sorted(set(candidate.evidence) | {"sponsor_intro_continuity"})),
            )
        )
    return tuple(output)


def refine_explicit_owned_shop(
    transcript: Transcript, candidate: CandidateSegment
) -> DetectedInterval | None:
    """Use creation and shop-ask cues as boundaries for an owned merchandise pitch."""
    indices = set(candidate.snippet_indices)
    members = [cue for cue in transcript.snippets if cue.index in indices]
    starts = [
        cue
        for cue in members
        if re.search(
            r"\bwe(?:'ve| have)?\s+(?:created|made|built)\b",
            cue.text.replace("’", "'"),
            re.IGNORECASE,
        )
    ]
    ends = [cue for cue in members if OWNED_SHOP.search(cue.text) and SHOP_ACTION.search(cue.text)]
    if not starts or not ends:
        return None
    first, last = starts[0], ends[-1]
    if last.end_seconds - first.start_seconds < 10:
        return None
    return DetectedInterval(
        start_seconds=first.start_seconds,
        end_seconds=last.end_seconds,
        score=candidate.score,
        evidence=candidate.evidence,
        snippet_indices=candidate.snippet_indices,
    )


class ContextualPromotionDetector(PromotionDetector):
    """Experimental candidate-discovery comparison against the unchanged rules baseline."""

    def __init__(self) -> None:
        super().__init__(classifier=ContextualRulesWindowClassifier())

    def detect(
        self, transcript: Transcript, sensitivity: Sensitivity = Sensitivity.CONSERVATIVE
    ) -> DetectionResult:
        windows = build_windows(
            transcript,
            window_seconds=self._window_seconds,
            overlap_seconds=self._overlap_seconds,
        )
        scores = tuple(self._classifier.score(window) for window in windows)
        candidates = assemble_candidates(windows, scores, self._classifier, sensitivity)
        bridged = bridge_sponsor_introductions(transcript, candidates)
        intervals = []
        for item in bridged:
            conventional = refine_boundaries(transcript, (item,), self._classifier, sensitivity)
            if conventional:
                intervals.extend(conventional)
            elif "owned_shop_action" in item.evidence:
                owned_interval = refine_explicit_owned_shop(transcript, item)
                if owned_interval is not None:
                    intervals.append(owned_interval)
        intervals = validate_intervals(intervals)
        return DetectionResult(
            video_id=transcript.video_id,
            sensitivity=sensitivity,
            intervals=intervals,
            window_count=len(windows),
        )
