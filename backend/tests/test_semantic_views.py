"""View construction keeps every source cue and forbids silent long-cue truncation."""

import re
import sys
from pathlib import Path
from types import SimpleNamespace

from ytsponsorskip.domain import Transcript, TranscriptSnippet

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/local-semantic"))
from views import build_views, split_text  # noqa: E402


class WordTokenizer:
    def encode(self, text, add_special_tokens=True):
        offsets = [match.span() for match in re.finditer(r"\S+", text)]
        return SimpleNamespace(
            ids=list(range(len(offsets) + (2 if add_special_tokens else 0))),
            offsets=offsets,
        )


def test_long_cue_views_preserve_exact_characters_and_token_limit():
    text = "  " + "  ".join(f"word{number}" for number in range(40)) + "\n"
    tokenizer = WordTokenizer()
    parts = split_text(text, tokenizer, 12)
    assert "".join(parts) == text
    assert all(len(tokenizer.encode(part).ids) <= 12 for part in parts)


def test_all_window_and_boundary_views_cover_every_original_identity():
    tokenizer = WordTokenizer()
    transcript = Transcript(
        "synthetic",
        "English",
        "en",
        None,
        tuple(
            TranscriptSnippet(index, (f"cue{index} " * 18), index * 10, 12) for index in range(5)
        ),
        "synthetic-unit-fixture",
        "1",
    )
    original = tuple(transcript.snippets)
    windows, contexts = build_views(transcript, tokenizer, max_tokens=12, overlap_tokens=3)
    assert {index for view in windows for index in view.snippet_indices} == set(range(5))
    assert {index for view in contexts for index in view.snippet_indices} == set(range(5))
    assert all(view.token_count <= 12 for view in windows + contexts)
    assert all(view.snippet_indices[0] in view.context_indices for view in contexts)
    assert transcript.snippets == original
