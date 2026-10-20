const test = require("node:test");
const assert = require("node:assert/strict");
const { localBackendUrl, validatePreviewResponse } = require("../preview-contract.js");

test("preview response requires matching video, request, mode, source and valid intervals", () => {
  const expected = { videoId: "094y1Z2wpJg", requestId: "request-1", mode: "conservative", source: "saved" };
  const body = {
    status: "ready", video_id: expected.videoId, request_id: expected.requestId,
    mode: expected.mode, transcript_source: expected.source,
    detector_version: "rules-test", transcript_provider: "saved-reviewed-tune",
    intervals: [
      { start_seconds: 10, end_seconds: 13 },
      { start_seconds: 20, end_seconds: 23.001 }
    ]
  };
  const result = validatePreviewResponse(body, expected);
  assert.equal(result.status, "predictions-available");
  assert.deepEqual(result.intervals.map(item => item.autoSkipEligible), [false, true]);
  assert.equal(validatePreviewResponse({ ...body, request_id: "stale" }, expected), null);
  assert.equal(validatePreviewResponse({ ...body, mode: "aggressive" }, expected), null);
  assert.equal(validatePreviewResponse({ ...body, transcript_source: "supadata" }, expected), null);
  assert.equal(validatePreviewResponse({ ...body, intervals: [{ start_seconds: 1, end_seconds: NaN }] }, expected), null);
  assert.equal(validatePreviewResponse({ ...body, intervals: [] }, expected).status, "no-promotions");
});

test("preview backend is restricted to the two permitted local origins", () => {
  assert.equal(localBackendUrl("http://127.0.0.1:8000"), "http://127.0.0.1:8000");
  assert.equal(localBackendUrl("http://localhost:8000/"), "http://localhost:8000");
  for (const value of ["https://example.com", "http://localhost:8001", "http://localhost:8000@evil.com", "http://127.0.0.1:8000/path"]) {
    assert.equal(localBackendUrl(value), null);
  }
});
