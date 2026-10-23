"""Exact-text, token-bounded analysis views with mappings to original cue identities."""

from dataclasses import dataclass


@dataclass(frozen=True)
class View:
    text: str
    snippet_indices: tuple[int, ...]
    context_indices: tuple[int, ...]
    token_count: int


def split_text(text, tokenizer, max_tokens):
    """Split only model input views, preserving every source character; never truncate."""
    remaining = text
    output = []
    while remaining:
        encoded = tokenizer.encode(remaining, add_special_tokens=False)
        if len(encoded.ids) <= max_tokens - 2:
            output.append(remaining)
            break
        end = encoded.offsets[max_tokens - 3][1]
        while end > 0 and len(tokenizer.encode(remaining[:end]).ids) > max_tokens:
            end -= 1
        if end <= 0:
            raise ValueError("Tokenizer cannot construct a bounded nonempty view")
        output.append(remaining[:end])
        remaining = remaining[end:]
    if "".join(output) != text:
        raise ValueError("Analysis view split lost source characters")
    return output


def build_views(transcript, tokenizer, *, max_tokens=224, overlap_tokens=32):
    """Scan all cues with overlapping token-bounded views, plus cue boundary contexts."""
    atoms = [
        (cue.index, part)
        for cue in transcript.snippets
        for part in split_text(cue.text, tokenizer, max_tokens)
    ]
    windows = []
    start = 0
    while start < len(atoms):
        end = start + 1
        while end < len(atoms):
            proposed = " ".join(text for _, text in atoms[start : end + 1])
            if len(tokenizer.encode(proposed).ids) > max_tokens:
                break
            end += 1
        text = " ".join(text for _, text in atoms[start:end])
        identities = tuple(dict.fromkeys(index for index, _ in atoms[start:end]))
        windows.append(View(text, identities, identities, len(tokenizer.encode(text).ids)))
        if end == len(atoms):
            break
        next_start = end
        overlap = 0
        while next_start > start + 1 and overlap < overlap_tokens:
            next_start -= 1
            overlap += len(tokenizer.encode(atoms[next_start][1], add_special_tokens=False).ids)
        start = next_start
    contexts = []
    for position, cue in enumerate(transcript.snippets):
        for part in split_text(cue.text, tokenizer, max_tokens):
            text = part
            context_ids = [cue.index]
            if position > 0:
                previous = transcript.snippets[position - 1]
                proposed = previous.text + " " + text
                if len(tokenizer.encode(proposed).ids) <= max_tokens:
                    text = proposed
                    context_ids.insert(0, previous.index)
            if position + 1 < len(transcript.snippets):
                following = transcript.snippets[position + 1]
                proposed = text + " " + following.text
                if len(tokenizer.encode(proposed).ids) <= max_tokens:
                    text = proposed
                    context_ids.append(following.index)
            contexts.append(
                View(text, (cue.index,), tuple(context_ids), len(tokenizer.encode(text).ids))
            )
    if {index for view in windows for index in view.snippet_indices} != {
        cue.index for cue in transcript.snippets
    }:
        raise ValueError("All-window coverage omitted a source cue")
    if any(view.token_count > max_tokens for view in windows + contexts):
        raise ValueError("Silent model truncation is forbidden")
    return windows, contexts
