#!/usr/bin/env python3
"""Render a saved tune evaluation as a self-contained HTML page and Markdown report."""

import argparse
import html
import json
from pathlib import Path

from evaluate_detector import sha256
from offline_common import (
    DETECTOR_SOURCE,
    ROOT,
    load_tune,
    subtract_ranges,
    trace_rules,
    verify_saved_evaluation,
    write_new,
)
from ytsponsorskip.detector import Sensitivity
from ytsponsorskip.evaluation import intersection_duration, merge_ranges, ranges_duration


def timestamp(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f"{int(minutes):02d}:{seconds:05.2f}".rstrip("0").rstrip(".")


def ranges_text(ranges):
    return (
        "; ".join(
            f"{timestamp(start)}–{timestamp(end)} ({start:g}–{end:g} s)" for start, end in ranges
        )
        or "None"
    )


def as_ranges(rows):
    return [(row["start_seconds"], row["end_seconds"]) for row in rows]


def review_video(video, labels, transcript, document, rows):
    modes = {}
    contexts = []
    source_span = [
        (
            transcript.snippets[0].start_seconds,
            max(snippet.end_seconds for snippet in transcript.snippets),
        )
    ]
    for mode in Sensitivity:
        row = rows[mode.value]
        annotations = as_ranges(row["annotations"])
        if annotations != labels:
            raise ValueError("Saved annotations differ from current tune labels")
        predictions = as_ranges(row["predictions"])
        trace = trace_rules(transcript, mode)  # no annotations passed into detector stages
        false_skips = subtract_ranges(predictions, labels)
        missed = subtract_ranges(labels, predictions)
        outside_source = subtract_ranges(missed, source_span)
        inside_source = subtract_ranges(missed, outside_source)
        outside_candidates = subtract_ranges(inside_source, trace["candidate_ranges"])
        refinement_loss = subtract_ranges(inside_source, outside_candidates)
        # Disjoint partition of missed time: unobserved / candidate omission / refinement loss.
        matched_predictions = {match["prediction_index"] for match in row["matches"]}
        matched_annotations = {match["annotation_index"] for match in row["matches"]}
        modes[mode.value] = {
            "predictions": row["predictions"],
            "false_skip_ranges": false_skips,
            "missed_ranges": missed,
            "candidate_ranges": trace["candidate_ranges"],
            "outside_observed_span": outside_source,
            "candidate_stage_missed_ranges": outside_candidates,
            "refinement_missed_ranges": refinement_loss,
            "unmatched_prediction_count": len(predictions) - len(matched_predictions),
            "unmatched_annotation_count": len(labels) - len(matched_annotations),
            "metrics": {
                key: row[key]
                for key in (
                    "incorrect_predicted_seconds",
                    "missed_promotional_seconds",
                    "matches",
                    "detection_runtime_ms",
                )
            },
        }
        for start, end in false_skips + missed:
            contexts.append((max(0, start - 8), end + 8))
        if not false_skips and not missed and labels:
            for start, end in labels:
                contexts += [(max(0, start - 8), start + 8), (max(0, end - 8), end + 8)]
        if not labels and not predictions and trace["highest_score_window"]:
            window = trace["highest_score_window"]
            contexts.append((window["start_seconds"], window["end_seconds"]))
    excerpts = []
    for start, end in merge_ranges(contexts):
        snippets = []
        for snippet in transcript.snippets:
            if snippet.start_seconds < end and snippet.end_seconds > start:
                cues = {}
                cue_range = [(snippet.start_seconds, snippet.end_seconds)]
                for mode, result in modes.items():
                    tags = []
                    if intersection_duration(cue_range, result["false_skip_ranges"]) > 0:
                        tags.append("false skip")
                    if intersection_duration(cue_range, result["missed_ranges"]) > 0:
                        tags.append("missed")
                    cues[mode] = ", ".join(tags) or "context"
                snippets.append(
                    {
                        "index": snippet.index,
                        "text": snippet.text,
                        "start": snippet.start_seconds,
                        "end": snippet.end_seconds,
                        "tags": cues,
                    }
                )
        excerpts.append({"start": start, "end": end, "snippets": snippets})
    return {
        "video_id": video["video_id"],
        "title": video["title"],
        "promotion_status": video["promotion_status"],
        "annotations": labels,
        "caption_type": document["transcript"].get("caption_type", "unknown"),
        "derived_durations": not document["timing"].get("source_duration_available", False),
        "source_span": source_span,
        "modes": modes,
        "excerpts": excerpts,
    }


def diagnosis(mode):
    return (
        f"Unmatched predictions: {mode['unmatched_prediction_count']}; "
        f"unmatched annotations: {mode['unmatched_annotation_count']}. "
        f"Missed within candidate spans (refinement/policy loss): "
        f"{ranges_duration(mode['refinement_missed_ranges']):g} s; "
        f"missed inside observed transcript but outside candidates: "
        f"{ranges_duration(mode['candidate_stage_missed_ranges']):g} s; "
        f"missed beyond observed analysis span: "
        f"{ranges_duration(mode['outside_observed_span']):g} s."
    )


def render_markdown(review):
    lines = [
        "# Tune error review — all 14 reviewed videos",
        "",
        "Generated from the preserved rules evaluation. Conservative is the primary review mode.",
        "Manual annotations are evaluation targets, not independently verified truth. "
        "No acquisition or model calls; held-out and partial reviews excluded.",
        "",
        "## Reading the report",
        "",
        "A matched prediction with an early/late edge is a boundary error; an unmatched "
        "prediction/annotation is a possible classification/assembly error. These are diagnostic "
        "categories, not proof of semantic cause. A separate label-free candidate trace locates "
        "where missed time was lost. Cue tags indicate overlap, not that the entire cue is wrong.",
        "All cue ends below are derived analysis spans. Source starts are preserved; silence, "
        "mixed-purpose speech, and the final-cue fallback make exact ends uncertain. "
        "Time beyond the observed span is not called a classifier failure.",
        "",
        "Metrics reuse half-open union/intersection arithmetic and greedy one-to-one "
        "maximum-overlap matching from evaluation.py; any positive overlap qualifies for matching. "
        "Boundary errors are absolute endpoint differences for matched pairs only.",
        "",
        f"Saved evaluation SHA-256: `{review['evaluation_sha256']}`.",
        "",
        "| Video | Annotated | Conservative | Aggressive | C false / missed | A false / missed |",
        "| --- | --- | --- | --- | ---: | ---: |",
    ]
    for video in review["videos"]:
        c, a = video["modes"]["conservative"], video["modes"]["aggressive"]
        lines.append(
            f"| [{video['video_id']}](https://www.youtube.com/watch?v={video['video_id']}) | "
            f"{ranges_text(video['annotations'])} | {ranges_text(as_ranges(c['predictions']))} | "
            f"{ranges_text(as_ranges(a['predictions']))} | "
            f"{c['metrics']['incorrect_predicted_seconds']:g} / "
            f"{c['metrics']['missed_promotional_seconds']:g} s | "
            f"{a['metrics']['incorrect_predicted_seconds']:g} / "
            f"{a['metrics']['missed_promotional_seconds']:g} s |"
        )
    for video in review["videos"]:
        lines += [
            "",
            f"## {video['title']} — {video['video_id']}",
            "",
            f"[Open video](https://www.youtube.com/watch?v={video['video_id']}). "
            f"Caption type: {video['caption_type']}. "
            f"Observed analysis span: {ranges_text(video['source_span'])}.",
            "",
            f"Annotated: **{ranges_text(video['annotations'])}**.",
            "",
        ]
        for note in video.get("review_notes", []):
            lines += [f"**Review interpretation (not a label edit):** {note}", ""]
        for name, mode in video["modes"].items():
            lines += [
                f"### {name.title()}",
                "",
                f"Predicted: {ranges_text(as_ranges(mode['predictions']))}.",
                "",
                f"False skips: {ranges_text(mode['false_skip_ranges'])}.",
                f"Missed: {ranges_text(mode['missed_ranges'])}.",
                "",
                diagnosis(mode),
                "",
                f"Candidate spans before refinement: {ranges_text(mode['candidate_ranges'])}.",
                "",
            ]
            for match in mode["metrics"]["matches"]:
                lines.append(
                    f"- Matched label {match['annotation_index'] + 1} / prediction "
                    f"{match['prediction_index'] + 1}: start error "
                    f"{match['start_error_seconds']:g} s, end error "
                    f"{match['end_error_seconds']:g} s."
                )
            if mode["predictions"]:
                lines += [
                    "",
                    "Rule evidence: "
                    + "; ".join(
                        ", ".join(prediction["evidence"]) for prediction in mode["predictions"]
                    )
                    + ".",
                ]
        lines += ["", "### Transcript context", ""]
        if not video["annotations"]:
            lines += [
                "Reviewed negative; no error in either mode. The highest-scoring rules "
                "window is shown for inspection, not as an error or a new label.",
                "",
            ]
        for excerpt in video["excerpts"]:
            lines += [f"Context {ranges_text([(excerpt['start'], excerpt['end'])])}:", ""]
            for snippet in excerpt["snippets"]:
                text = snippet["text"].replace("\n", " ").rstrip()
                lines.append(
                    f"> [{timestamp(snippet['start'])}–{timestamp(snippet['end'])}†] "
                    f"cue #{snippet['index']} · C: {snippet['tags']['conservative']} · "
                    f"A: {snippet['tags']['aggressive']} — {text}\n"
                )
        lines += ["† End is derived, not a source-supplied speech or promotion boundary."]
    return "\n".join(lines) + "\n"


STYLE = """
:root{font:16px/1.5 system-ui,sans-serif;color:#193044;background:#f4f6f8}
body{max-width:1180px;margin:0 auto;padding:32px}h1{font-size:2.2rem;margin-bottom:8px}
a{color:#075ca0}header{margin-bottom:28px}.lede{max-width:85ch;color:#465b6b}
.toolbar{position:sticky;top:0;background:#e7eef5;padding:14px;z-index:2;border-radius:10px;
display:flex;gap:20px;align-items:center;flex-wrap:wrap}input,select{font:inherit;padding:7px}
article{background:white;margin:24px 0;border:1px solid #cfdae3;border-radius:12px;padding:24px}
h2{margin:0 0 8px;font-size:1.35rem}.meta,.note{color:#526677;font-size:.9rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px}
.mode{padding:16px;background:#f7f9fc;border-left:4px solid #1e708b;border-radius:5px}
.aggressive{border-left-color:#ae6221}.metrics{font-weight:650}.error{color:#8b283b}
details{margin-top:20px}summary{cursor:pointer;font-weight:650}.cue{padding:10px 0;
border-bottom:1px solid #e3e8ec;display:grid;grid-template-columns:150px 1fr;gap:14px}
.cue p{margin:0;white-space:pre-wrap}.tag{font-size:.78rem;display:block;color:#835021}
[hidden]{display:none!important}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%}
td,th{text-align:left;padding:10px;border-bottom:1px solid #d5dfe7;vertical-align:top}
@media(max-width:650px){body{padding:12px}.cue{grid-template-columns:1fr}article{padding:16px}}
@media print{.toolbar{display:none}details{display:block}article{break-inside:avoid}}
"""


def render_html(review):
    esc = html.escape
    parts = [
        "<!doctype html><html lang='en'><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; "
        "style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'\">",
        "<title>SponsorSkip · tune error review</title>",
        f"<style>{STYLE}</style><body>",
        "<header><p>SPONSORSKIP / OFFLINE EVALUATION</p><h1>Where the detector loses time</h1>",
        "<p class='lede'>14 reviewed tune videos · unchanged rules · saved predictions. "
        "Compare intervals and inspect the original timestamped cues. "
        "Annotations are manual judgments. Cue ends (†) are derived and approximate.</p>",
        "<p class='note'>No model calls or acquisition. No external resources load. "
        "YouTube opens only when you click a link. Held-out and partial reviews excluded.</p>",
        "<div class='table-wrap'><table><tr><th>Mode</th><th>False skip</th><th>Missed</th>"
        "<th>Negative videos affected</th><th>Matched</th><th>Start / end MAE</th></tr>",
    ]
    for mode, summary in review["summary"].items():
        parts.append(
            f"<tr><td>{esc(mode.title())}</td>"
            f"<td>{summary['incorrect_predicted_seconds']:g} s</td>"
            f"<td>{summary['missed_promotional_seconds']:g} s</td>"
            f"<td>{summary['negative_videos_with_any_predicted_skip']}/"
            f"{summary['evaluated_negative_video_count']}</td>"
            f"<td>{summary['matched_segment_count']}</td>"
            f"<td>{summary['mean_start_boundary_error_seconds']:g} / "
            f"{summary['mean_end_boundary_error_seconds']:g} s</td></tr>"
        )
    parts += [
        "</table></div></header><div class='toolbar'>",
        "<label>Mode <select id='mode'><option value='conservative'>Conservative</option>"
        "<option value='both'>Compare both</option><option value='aggressive'>Aggressive</option>"
        "</select></label><label>Find video <input id='search' type='search' "
        "placeholder='Title or video ID'></label><label><input id='errors' type='checkbox'> "
        "Only errors</label><span id='count' role='status'></span></div><main>",
    ]
    for video in review["videos"]:
        vid = video["video_id"]
        flags = {
            name: bool(mode["false_skip_ranges"] or mode["missed_ranges"])
            for name, mode in video["modes"].items()
        }
        parts += [
            f"<article data-search='{esc((video['title'] + ' ' + vid).lower(), quote=True)}' "
            f"data-conservative='{str(flags['conservative']).lower()}' "
            f"data-aggressive='{str(flags['aggressive']).lower()}'>",
            f"<h2><a href='https://www.youtube.com/watch?v={vid}' target='_blank' "
            f"rel='noopener noreferrer'>{esc(video['title'])}</a></h2>",
            f"<p class='meta'>{vid} · {esc(video['caption_type'])} captions · "
            f"{esc(video['promotion_status'])}</p>",
            f"<p><strong>Annotated</strong> {ranges_text(video['annotations'])}</p>",
        ]
        for note in video.get("review_notes", []):
            parts += [f"<p><strong>Review interpretation:</strong> {esc(note)}</p>"]
        parts += ["<div class='grid'>"]
        for name, mode in video["modes"].items():
            parts += [
                f"<section class='mode {name}' data-mode='{name}'>",
                f"<h3>{name.title()}</h3><p><strong>Predicted</strong> "
                f"{ranges_text(as_ranges(mode['predictions']))}</p>",
                f"<p class='metrics'>{mode['metrics']['incorrect_predicted_seconds']:g} s "
                f"false · {mode['metrics']['missed_promotional_seconds']:g} s missed</p>",
                f"<p class='error'>False: {ranges_text(mode['false_skip_ranges'])}<br>"
                f"Missed: {ranges_text(mode['missed_ranges'])}</p>",
                f"<p>{diagnosis(mode)}</p><p class='note'>Candidate spans: "
                f"{ranges_text(mode['candidate_ranges'])}</p>",
            ]
            for match in mode["metrics"]["matches"]:
                parts.append(
                    f"<p class='note'>Label {match['annotation_index'] + 1}: "
                    f"start error {match['start_error_seconds']:g} s; "
                    f"end error {match['end_error_seconds']:g} s.</p>"
                )
            parts += ["</section>"]
        parts += ["</div><details><summary>Timestamped transcript context</summary>"]
        if not video["annotations"]:
            parts += [
                "<p class='note'>Reviewed negative with no skips. Highest-scoring rule "
                "window shown for inspection; it is not an error.</p>"
            ]
        for excerpt in video["excerpts"]:
            parts += [f"<h4>{ranges_text([(excerpt['start'], excerpt['end'])])}</h4>"]
            for cue in excerpt["snippets"]:
                parts += [
                    "<div class='cue'><div>",
                    f"<a href='https://www.youtube.com/watch?v={vid}&amp;t={int(cue['start'])}' "
                    f"target='_blank' rel='noopener noreferrer'>{timestamp(cue['start'])}"
                    f"–{timestamp(cue['end'])}†</a><br><small>cue #{cue['index']}</small>",
                ]
                for name, tag in cue["tags"].items():
                    parts.append(
                        f"<span class='tag' data-mode='{name}'>{name.title()}: {esc(tag)}</span>"
                    )
                parts += [f"</div><p>{esc(cue['text'])}</p></div>"]
        parts += ["</details></article>"]
    parts += [
        "</main><script>",
        """
const mode = document.querySelector('#mode');
const search = document.querySelector('#search');
const errors = document.querySelector('#errors');
function render() {
  document.querySelectorAll('[data-mode]').forEach(el => {
    el.hidden = mode.value !== 'both' && el.dataset.mode !== mode.value;
  });
  let visible = 0;
  document.querySelectorAll('article').forEach(el => {
    const hasError = mode.value === 'both'
      ? el.dataset.conservative === 'true' || el.dataset.aggressive === 'true'
      : el.dataset[mode.value] === 'true';
    el.hidden = !el.dataset.search.includes(search.value.trim().toLowerCase())
      || (errors.checked && !hasError);
    if (!el.hidden) visible++;
  });
  document.querySelector('#count').textContent = `${visible} videos shown`;
}
[mode, search, errors].forEach(el => el.addEventListener('input', render));
render();
""",
        "</script></body></html>",
    ]
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evaluation", type=Path, default=ROOT / "data/evaluation/tune-rules-3c35ceb.json"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--videos", type=Path, default=ROOT / "data/validation/videos.csv")
    parser.add_argument("--segments", type=Path, default=ROOT / "data/validation/segments.csv")
    parser.add_argument("--notes", type=Path, default=ROOT / "data/reviews/tune-review-notes.json")
    args = parser.parse_args()
    for name in ("index.html", "error-review.md", "review.json"):
        if (args.output_dir / name).exists():
            parser.error("Review output exists; choose a new directory")
    saved = json.loads(args.evaluation.read_text())
    videos, labels, transcripts, documents, hashes, exclusions = load_tune(
        videos_path=args.videos, segments_path=args.segments
    )
    verify_saved_evaluation(saved, videos, hashes)
    if saved["detector"]["source_sha256"] != sha256(DETECTOR_SOURCE):
        parser.error("Stage tracing requires the exact recorded detector source")
    if exclusions:
        parser.error("Review requires all saved tune transcripts")
    rows = {
        name: {row["video_id"]: row for row in summary["per_video"]}
        for name, summary in saved["modes"].items()
    }
    notes = json.loads(args.notes.read_text())
    if set(notes) - set(hashes):
        parser.error("Review notes reference a video outside reviewed tune")
    review = {
        "schema_version": 1,
        "evaluation_sha256": sha256(args.evaluation),
        "review_notes_sha256": sha256(args.notes),
        "transcript_hashes": hashes,
        "summary": {
            name: {k: v for k, v in summary.items() if k != "per_video"}
            for name, summary in saved["modes"].items()
        },
        "videos": [
            review_video(
                video,
                labels[video["video_id"]],
                transcripts[video["video_id"]],
                documents[video["video_id"]],
                {name: per_video[video["video_id"]] for name, per_video in rows.items()},
            )
            for video in videos
        ],
    }
    for video in review["videos"]:
        video["review_notes"] = notes.get(video["video_id"], [])
    write_new(args.output_dir / "index.html", render_html(review))
    write_new(args.output_dir / "error-review.md", render_markdown(review))
    write_new(args.output_dir / "review.json", json.dumps(review, indent=2) + "\n")
    print(f"Reviewed {len(review['videos'])} videos: {args.output_dir / 'index.html'}")


if __name__ == "__main__":
    main()
