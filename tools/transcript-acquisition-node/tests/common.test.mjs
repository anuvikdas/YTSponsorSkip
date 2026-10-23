import assert from "node:assert/strict";
import test from "node:test";

import { completenessMetadata, normalizedDocument, overlapCount } from "../scripts/common.mjs";

const snippets = [
  { index: 0, text: "first", start_seconds: 0, duration_seconds: 2 },
  { index: 1, text: "second", start_seconds: 1.5, duration_seconds: 2 },
  { index: 2, text: "third", start_seconds: 4, duration_seconds: 1 }
];

test("overlap count preserves adjacent source timing relationships", () => {
  assert.equal(overlapCount(snippets), 1);
});

test("completeness metadata reports transcript extent without claiming exact boundaries", () => {
  const metadata = completenessMetadata(snippets, 8, ["test evidence"]);

  assert.equal(metadata.raw_segment_count, 3);
  assert.equal(metadata.first_start_seconds, 0);
  assert.equal(metadata.last_end_seconds, 5);
  assert.equal(metadata.trailing_gap_seconds, 3);
  assert.equal(metadata.overlapping_adjacent_snippets, 1);
  assert.equal(metadata.truncation_status, "no_evidence_detected");
});

test("unknown caption type remains unknown instead of becoming manual", () => {
  const document = normalizedDocument({
    videoId: "U3aXWizDbQ4",
    library: "test-library",
    version: "1.0.0",
    language: "English",
    languageCode: "en",
    captionType: "unknown",
    captionTypeEvidence: "track metadata absent",
    latencyMs: 1,
    snippets,
    sourceTimingUnit: "seconds",
    completeness: completenessMetadata(snippets, null, [])
  });

  assert.equal(document.transcript.caption_type, "unknown");
  assert.equal(document.transcript.is_generated, null);
});
