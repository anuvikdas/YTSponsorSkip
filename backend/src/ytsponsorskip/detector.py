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

    def supports(self, score: WindowScore, sensitivity: Sensitivity) -> bool:
        """Return whether a neighboring window can extend an anchored candidate."""


EVIDENCE_WEIGHTS = {
    "disclosure": 3,
    "affiliate": 3,
    "creator_owned": 3,
    "membership": 2,
    "offer": 2,
    "cta": 2,
    "url": 2,
    "sales": 2,
    "transition": 1,
}

EVIDENCE_PATTERNS = {
    "disclosure": re.compile(
        r"\b(?:sponsor(?:ed|ing|ship)?(?:\s+(?:by|of|for|this|our|the|a)\b)?|"
        r"thanks? to .{0,100} for sponsor(?:ing|ship)|paid partnership|brought to you by|"
        r"today'?s sponsor|segue to (?:our|the) sponsor)\b",
        re.IGNORECASE,
    ),
    "affiliate": re.compile(
        r"\b(?:affiliate links?|earn (?:a )?commission|commission from|support (?:me|us|the "
        r"channel) (?:by|when))\b",
        re.IGNORECASE,
    ),
    "creator_owned": re.compile(
        r"\b(?:(?:my|our) (?:course|book|merch(?:andise)?|app|product|service|store|shop|"
        r"newsletter|membership|patreon|subscription|kit|box|project)|"
        r"(?:i|we|we'?ve) (?:made|launched|created|built|developed|are (?:finally )?launching) "
        r"(?:a|an|my|our)?\s*(?:new )?(?:app|course|book|shop|store|product|service|"
        r"membership|subscription|kit|box|project)|(?:working on|launching).{0,30}"
        r"(?:app|course|book|shop|store|product|service|membership|subscription)|"
        r"support(?:ing)? (?:these|my|our) videos? "
        r"on patreon|(?:book.{0,100}(?:founder|head writer)|(?:founder|head writer).{0,100}"
        r"book))\b",
        re.IGNORECASE,
    ),
    "membership": re.compile(
        r"\b(?:patreon|patrons?|channel membership|become a member|support(?:ing)? "
        r"(?:these|my|our) videos?)\b",
        re.IGNORECASE,
    ),
    "offer": re.compile(
        r"\b(?:promo(?:tional)? code|coupon|free trial|discount|\d{1,2}\s*% off|save "
        r"(?:\d{1,2}\s*%|\d{1,2}\s*percent|money)|\d{1,2}\s*percent off|"
        r"limited[- ]time offer|"
        r"\d+ months? free|holiday special|"
        r"pre[- ]?order(?:ing)?|subscription)(?=\W|$)",
        re.IGNORECASE,
    ),
    "cta": re.compile(
        r"\b(?:use (?:my |our )?code|(?:that|the|my|our)?\s*link.{0,35}(?:description|below)|"
        r"check (?:it|them|us|these) out|sign up|shop now|order now|buy now|join "
        r"(?:me|my|our|the)|become a member|visit (?:my|our|the)|head (?:to|over to)|"
        r"go to|learn more|pick it up|get (?:it|one|something) (?:now|from)|download|"
        r"browse (?:my|our|the)|pre[- ]?order)\b",
        re.IGNORECASE,
    ),
    "url": re.compile(
        r"\b(?:[a-z0-9][a-z0-9-]*\s*(?:\.|dot)\s*(?:com|org|net|io)\b|"
        r"(?:my|our|their|the) website\b)",
        re.IGNORECASE,
    ),
    "transition": re.compile(
        r"\b(?:before we (?:continue|begin|get started)|quick word|a word from|take a moment "
        r"to thank|but first)\b",
        re.IGNORECASE,
    ),
}

PRODUCT_PATTERN = re.compile(
    r"\b(?:app|website|service|software|platform|(?:my|our|their|the|a|an|online) course|"
    r"book|subscription|membership|"
    r"patreon|shop|store|merch(?:andise)?|product|lineup|device|system|templates?|domain|"
    r"kit|build box|power bank|charging station|storage|nas|wallpapers?)\b",
    re.IGNORECASE,
)

COMMERCIAL_PATTERN = re.compile(
    r"\b(?:helps? you|lets? you|allows? you|offers?|provides?|features?|comes with|supports?|"
    r"delivered|available|finally live|launch(?:ed|ing)?|built[- ]in|one[- ]stop shop|"
    r"pick one|choose a template|works with|designed to|recommend|publish|register|charges?|"
    r"get started|get your|make (?:a|your)|build (?:a|your)|run your|sell|"
    r"split(?:ting)? profits|out now)\b",
    re.IGNORECASE,
)

RETURN_TO_CONTENT = re.compile(
    r"\b(?:now back to|back to (?:the|our|what)|let'?s get back to|anyway,? back to|"
    r"that'?s been it|thanks for watching|catch you .{0,30} next one)\b",
    re.IGNORECASE,
)

BOUNDARY_EVIDENCE = frozenset(
    {
        "disclosure",
        "affiliate",
        "creator_owned",
        "membership",
        "offer",
        "url",
        "sales",
        "transition",
    }
)


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("’", "'").replace("–", "-")).strip()


class RulesWindowClassifier:
    """Deterministic zero-cost baseline; scores are not calibrated probabilities."""

    def score(self, window: TranscriptWindow) -> WindowScore:
        text = _normalized_text(window.text)
        evidence = [
            label for label, pattern in EVIDENCE_PATTERNS.items() if pattern.search(text)
        ]
        if PRODUCT_PATTERN.search(text) and COMMERCIAL_PATTERN.search(text):
            evidence.append("sales")
        evidence_tuple = tuple(evidence)
        return WindowScore(
            score=sum(EVIDENCE_WEIGHTS[label] for label in evidence_tuple),
            evidence=evidence_tuple,
        )

    def qualifies(self, score: WindowScore, sensitivity: Sensitivity) -> bool:
        evidence = set(score.evidence)
        disclosure_pitch = "disclosure" in evidence and bool(
            evidence & {"url", "sales"}
        )
        creator_pitch = "creator_owned" in evidence and bool(
            evidence & {"cta", "offer", "url", "membership"}
        )
        affiliate_pitch = "affiliate" in evidence and bool(evidence & {"cta", "offer", "url"})
        direct_sales_pitch = (
            "sales" in evidence and len(evidence & {"cta", "offer", "url"}) >= 2
        ) or {"cta", "offer"} <= evidence
        if sensitivity is Sensitivity.CONSERVATIVE:
            return (
                score.score >= 5
                and (disclosure_pitch or creator_pitch or affiliate_pitch)
            ) or (score.score >= 4 and direct_sales_pitch)
        anchored_pitch = (
            disclosure_pitch
            or creator_pitch
            or affiliate_pitch
            or (
                bool(evidence & {"disclosure", "creator_owned", "affiliate"})
                and bool(evidence & {"cta", "offer", "url", "sales", "membership"})
            )
        )
        return score.score >= 4 and (
            anchored_pitch
            or direct_sales_pitch
            or ("sales" in evidence and bool(evidence & {"cta", "offer", "url"}))
        )

    def supports(self, score: WindowScore, sensitivity: Sensitivity) -> bool:
        evidence = set(score.evidence)
        minimum_score = 2
        return score.score >= minimum_score and bool(
            evidence
            & {
                "disclosure",
                "affiliate",
                "creator_owned",
                "membership",
                "offer",
                "cta",
                "url",
                "sales",
            }
        )


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
    anchor_positions = {
        position
        for position, score in enumerate(scores)
        if classifier.qualifies(score, sensitivity)
    }
    if not anchor_positions:
        return ()

    selected_positions = set(anchor_positions)
    neutral_limit = 1 if sensitivity is Sensitivity.CONSERVATIVE else 2
    for anchor_position in anchor_positions:
        position = anchor_position - 1
        pending_neutral: list[int] = []
        while position >= 0:
            if windows[position].end_seconds < windows[position + 1].start_seconds:
                break
            if classifier.supports(scores[position], sensitivity):
                if pending_neutral and not set(scores[position].evidence) & {
                    "disclosure",
                    "affiliate",
                    "creator_owned",
                    "membership",
                }:
                    break
                selected_positions.update(pending_neutral)
                selected_positions.add(position)
                pending_neutral.clear()
            elif len(pending_neutral) < neutral_limit:
                pending_neutral.append(position)
            else:
                break
            position -= 1
        position = anchor_position + 1
        pending_neutral = []
        while position < len(windows):
            if windows[position].start_seconds > windows[position - 1].end_seconds:
                break
            if classifier.supports(scores[position], sensitivity):
                if pending_neutral and not set(scores[position].evidence) & {
                    "disclosure",
                    "affiliate",
                    "creator_owned",
                    "membership",
                }:
                    break
                selected_positions.update(pending_neutral)
                selected_positions.add(position)
                pending_neutral.clear()
            elif len(pending_neutral) < neutral_limit:
                pending_neutral.append(position)
            else:
                break
            position += 1

    selected = [(windows[position], scores[position]) for position in sorted(selected_positions)]
    join_gap = 20.0 if sensitivity is Sensitivity.CONSERVATIVE else 30.0
    groups: list[list[tuple[TranscriptWindow, WindowScore]]] = []
    for window, score in selected:
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


def _span_window(snippets: Sequence[TranscriptSnippet]) -> TranscriptWindow:
    return TranscriptWindow(
        window_id=snippets[0].index,
        start_seconds=snippets[0].start_seconds,
        end_seconds=max(snippet.end_seconds for snippet in snippets),
        snippet_indices=tuple(snippet.index for snippet in snippets),
        text=" ".join(snippet.text for snippet in snippets),
    )


def _boundary_signal_positions(
    members: Sequence[TranscriptSnippet],
    classifier: WindowClassifier,
    sensitivity: Sensitivity,
) -> set[int]:
    signal_positions: set[int] = set()
    individual_scores = [classifier.score(_snippet_window(snippet)) for snippet in members]
    for position, score in enumerate(individual_scores):
        if set(score.evidence) & BOUNDARY_EVIDENCE:
            signal_positions.add(position)
    for position in range(len(members)):
        for span_size in (2, 3):
            end = position + span_size
            if end > len(members):
                break
            score = classifier.score(_span_window(members[position:end]))
            individual_evidence = set().union(
                *(set(member_score.evidence) for member_score in individual_scores[position:end])
            )
            combined_only_evidence = set(score.evidence) - individual_evidence
            if combined_only_evidence & BOUNDARY_EVIDENCE:
                signal_positions.update(range(position, end))
            member_qualifies = any(
                classifier.qualifies(member_score, sensitivity)
                for member_score in individual_scores[position:end]
            )
            if classifier.qualifies(score, sensitivity) and not member_qualifies:
                positions_with_evidence = {
                    member_position
                    for member_position in range(position, end)
                    if individual_scores[member_position].evidence
                }
                signal_positions.update(positions_with_evidence)
                if combined_only_evidence:
                    signal_positions.update(range(position, end))
    return signal_positions


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
        members = sorted(
            (by_index[index] for index in candidate.snippet_indices if index in by_index),
            key=lambda snippet: snippet.start_seconds,
        )
        signal_positions = _boundary_signal_positions(members, classifier, sensitivity)
        if not signal_positions:
            continue
        first = members[min(signal_positions)]
        last = members[max(signal_positions)]
        first_position = positions[first.index]
        last_position = positions[last.index]

        minimum_duration = 10.0
        if last.end_seconds - first.start_seconds < minimum_duration:
            continue

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

        if end_seconds - first.start_seconds >= minimum_duration:
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
