import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Protocol

from ytsponsorskip.domain import Transcript, TranscriptSnippet


class Sensitivity(StrEnum):
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"


@dataclass(frozen=True, slots=True)
class TranscriptWindow:
    window_id: int
    start_seconds: float
    end_seconds: float
    snippet_indices: tuple[int, ...]
    text: str


@dataclass(frozen=True, slots=True)
class WindowScore:
    score: int
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateSegment:
    window_ids: tuple[int, ...]
    snippet_indices: tuple[int, ...]
    score: int
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DetectedInterval:
    start_seconds: float
    end_seconds: float
    score: int
    evidence: tuple[str, ...]
    snippet_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DetectionResult:
    video_id: str
    sensitivity: Sensitivity
    intervals: tuple[DetectedInterval, ...]
    window_count: int


class WindowClassifier(Protocol):
    """Replaceable context-window classifier for offline comparison."""

    def score(self, window: TranscriptWindow) -> WindowScore:
        """Return a heuristic score and auditable evidence labels."""

    def qualifies(self, score: WindowScore, sensitivity: Sensitivity) -> bool:
        """Apply a policy threshold to a score."""


EVIDENCE_WEIGHTS = {
    "disclosure": 4,
    "affiliate": 3,
    "creator_owned": 3,
    "offer": 2,
    "cta": 2,
    "transition": 1,
}

EVIDENCE_PATTERNS = {
    "disclosure": re.compile(
        r"\b(?:sponsored by|sponsor(?:ed|ship) this|thanks? to .{0,60} for sponsor(?:ing|ship)|"
        r"paid partnership|brought to you by|today'?s sponsor)\b",
        re.IGNORECASE,
    ),
    "affiliate": re.compile(
        r"\b(?:affiliate links?|earn (?:a )?commission|commission from|support (?:me|us|the "
        r"channel) (?:by|when))\b",
        re.IGNORECASE,
    ),
    "creator_owned": re.compile(
        r"\b(?:(?:my|our) (?:course|book|merch(?:andise)?|app|product|service|store|"
        r"newsletter|membership|patreon)|(?:i|we) (?:made|launched|created) (?:a|an|my|our))\b",
        re.IGNORECASE,
    ),
    "offer": re.compile(
        r"\b(?:promo(?:tional)? code|coupon|free trial|discount|\d{1,2}% off|save "
        r"(?:\d{1,2}%|money)|limited[- ]time offer)\b",
        re.IGNORECASE,
    ),
    "cta": re.compile(
        r"\b(?:use (?:my |our )?code|link (?:is )?in (?:the )?description|check (?:it|them|"
        r"us) out|sign up|shop now|order now|buy now|join (?:my|our|the)|become a member|"
        r"visit (?:my|our|the)|head (?:to|over to))\b",
        re.IGNORECASE,
    ),
    "transition": re.compile(
        r"\b(?:before we (?:continue|begin|get started)|quick word|a word from|take a moment "
        r"to thank|but first)\b",
        re.IGNORECASE,
    ),
}

RETURN_TO_CONTENT = re.compile(
    r"\b(?:now back to|back to (?:the|our|what)|let'?s get back to|anyway,? back to)\b",
    re.IGNORECASE,
)


class RulesWindowClassifier:
    """Deterministic zero-cost baseline; scores are not calibrated probabilities."""

    def score(self, window: TranscriptWindow) -> WindowScore:
        evidence = tuple(
            label for label, pattern in EVIDENCE_PATTERNS.items() if pattern.search(window.text)
        )
        return WindowScore(
            score=sum(EVIDENCE_WEIGHTS[label] for label in evidence),
            evidence=evidence,
        )

    def qualifies(self, score: WindowScore, sensitivity: Sensitivity) -> bool:
        evidence = set(score.evidence)
        creator_pitch = "creator_owned" in evidence and bool({"cta", "offer"} & evidence)
        affiliate_pitch = "affiliate" in evidence and bool({"cta", "offer"} & evidence)
        if sensitivity is Sensitivity.CONSERVATIVE:
            return score.score >= 4 and (
                "disclosure" in evidence or creator_pitch or affiliate_pitch
            )
        promotional_context = bool({"disclosure", "creator_owned", "affiliate"} & evidence)
        action_or_separation = bool({"cta", "offer", "transition", "disclosure"} & evidence)
        return score.score >= 3 and promotional_context and action_or_separation


def build_windows(
    transcript: Transcript,
    *,
    window_seconds: float = 30.0,
    overlap_seconds: float = 15.0,
) -> tuple[TranscriptWindow, ...]:
    if not isfinite(window_seconds) or not isfinite(overlap_seconds):
        raise ValueError("window and overlap must be finite")
    if window_seconds <= 0 or overlap_seconds < 0 or overlap_seconds >= window_seconds:
        raise ValueError("require window_seconds > overlap_seconds >= 0")
    if not transcript.snippets:
        return ()

    snippets = tuple(sorted(transcript.snippets, key=lambda snippet: snippet.start_seconds))
    first_start = snippets[0].start_seconds
    observed_end = max(snippet.end_seconds for snippet in snippets)
    stride = window_seconds - overlap_seconds
    cursor = first_start
    windows: list[TranscriptWindow] = []
    seen_identities: set[tuple[int, ...]] = set()

    while cursor < observed_end:
        boundary = cursor + window_seconds
        members = tuple(
            snippet
            for snippet in snippets
            if snippet.start_seconds < boundary and snippet.end_seconds > cursor
        )
        identities = tuple(snippet.index for snippet in members)
        if members and identities not in seen_identities:
            seen_identities.add(identities)
            windows.append(
                TranscriptWindow(
                    window_id=len(windows),
                    start_seconds=cursor,
                    end_seconds=min(boundary, observed_end),
                    snippet_indices=identities,
                    text=" ".join(snippet.text for snippet in members),
                )
            )
        cursor += stride
    return tuple(windows)


def assemble_candidates(
    windows: Sequence[TranscriptWindow],
    scores: Sequence[WindowScore],
    classifier: WindowClassifier,
    sensitivity: Sensitivity,
) -> tuple[CandidateSegment, ...]:
    if len(windows) != len(scores):
        raise ValueError("every window must have exactly one score")
    qualifying = [
        (window, score)
        for window, score in zip(windows, scores, strict=True)
        if classifier.qualifies(score, sensitivity)
    ]
    if not qualifying:
        return ()

    join_gap = 5.0 if sensitivity is Sensitivity.CONSERVATIVE else 15.0
    groups: list[list[tuple[TranscriptWindow, WindowScore]]] = []
    for window, score in qualifying:
        if groups and window.start_seconds <= groups[-1][-1][0].end_seconds + join_gap:
            groups[-1].append((window, score))
        else:
            groups.append([(window, score)])

    candidates = []
    for group in groups:
        candidates.append(
            CandidateSegment(
                window_ids=tuple(window.window_id for window, _ in group),
                snippet_indices=tuple(
                    sorted({index for window, _ in group for index in window.snippet_indices})
                ),
                score=max(score.score for _, score in group),
                evidence=tuple(sorted({label for _, score in group for label in score.evidence})),
            )
        )
    return tuple(candidates)


def _snippet_window(snippet: TranscriptSnippet) -> TranscriptWindow:
    return TranscriptWindow(
        window_id=snippet.index,
        start_seconds=snippet.start_seconds,
        end_seconds=snippet.end_seconds,
        snippet_indices=(snippet.index,),
        text=snippet.text,
    )


def refine_boundaries(
    transcript: Transcript,
    candidates: Sequence[CandidateSegment],
    classifier: WindowClassifier,
    sensitivity: Sensitivity,
) -> tuple[DetectedInterval, ...]:
    by_index = {snippet.index: snippet for snippet in transcript.snippets}
    ordered = tuple(sorted(transcript.snippets, key=lambda snippet: snippet.start_seconds))
    positions = {snippet.index: position for position, snippet in enumerate(ordered)}
    intervals: list[DetectedInterval] = []

    for candidate in candidates:
        members = [by_index[index] for index in candidate.snippet_indices if index in by_index]
        signal_members = [
            snippet for snippet in members if classifier.score(_snippet_window(snippet)).evidence
        ]
        if not signal_members:
            continue
        first = min(signal_members, key=lambda snippet: snippet.start_seconds)
        last = max(signal_members, key=lambda snippet: snippet.end_seconds)
        first_position = positions[first.index]
        last_position = positions[last.index]

        if sensitivity is Sensitivity.AGGRESSIVE and first_position > 0:
            previous = ordered[first_position - 1]
            if first.start_seconds - previous.end_seconds <= 4:
                first = previous
                first_position -= 1
        if sensitivity is Sensitivity.AGGRESSIVE and last_position + 1 < len(ordered):
            following = ordered[last_position + 1]
            if following.start_seconds - last.end_seconds <= 4:
                last = following
                last_position += 1

        end_seconds = last.end_seconds
        search_end = min(len(ordered), last_position + 3)
        for snippet in ordered[first_position + 1 : search_end]:
            if RETURN_TO_CONTENT.search(snippet.text):
                end_seconds = snippet.start_seconds
                break

        if end_seconds > first.start_seconds:
            intervals.append(
                DetectedInterval(
                    start_seconds=first.start_seconds,
                    end_seconds=end_seconds,
                    score=candidate.score,
                    evidence=candidate.evidence,
                    snippet_indices=candidate.snippet_indices,
                )
            )
    return validate_intervals(intervals)


def validate_intervals(intervals: Sequence[DetectedInterval]) -> tuple[DetectedInterval, ...]:
    valid = sorted(
        (
            interval
            for interval in intervals
            if isfinite(interval.start_seconds)
            and isfinite(interval.end_seconds)
            and interval.start_seconds >= 0
            and interval.end_seconds > interval.start_seconds
        ),
        key=lambda interval: (interval.start_seconds, interval.end_seconds),
    )
    merged: list[DetectedInterval] = []
    for interval in valid:
        if merged and interval.start_seconds <= merged[-1].end_seconds:
            previous = merged[-1]
            merged[-1] = DetectedInterval(
                start_seconds=previous.start_seconds,
                end_seconds=max(previous.end_seconds, interval.end_seconds),
                score=max(previous.score, interval.score),
                evidence=tuple(sorted(set(previous.evidence) | set(interval.evidence))),
                snippet_indices=tuple(
                    sorted(set(previous.snippet_indices) | set(interval.snippet_indices))
                ),
            )
        else:
            merged.append(interval)
    return tuple(merged)


class PromotionDetector:
    def __init__(
        self,
        classifier: WindowClassifier | None = None,
        *,
        window_seconds: float = 30.0,
        overlap_seconds: float = 15.0,
    ) -> None:
        self._classifier = classifier or RulesWindowClassifier()
        self._window_seconds = window_seconds
        self._overlap_seconds = overlap_seconds

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
        intervals = refine_boundaries(
            transcript,
            candidates,
            self._classifier,
            sensitivity,
        )
        return DetectionResult(
            video_id=transcript.video_id,
            sensitivity=sensitivity,
            intervals=intervals,
            window_count=len(windows),
        )
