const test = require("node:test");
const assert = require("node:assert/strict");

const { CHANNEL, validateEnvelope } = require("../browser-transcript-provider.js");

const videoId = "dQw4w9WgXcQ";
const requestId = `${videoId}-12345678-request`;

function successEnvelope(overrides = {}) {
  return {
    channel: CHANNEL,
    type: "result",
    videoId,
    requestId,
    ok: true,
    payload: {
      language: "English",
      languageCode: "en",
      isGenerated: false,
      providerLatencyMs: 123.4,
      metadataDiscoveryMs: 23.4,
      timedTextFetchMs: 100,
      snippets: [
        { index: 0, text: "one", startSeconds: 0, durationSeconds: 2 },
        { index: 1, text: "two", startSeconds: 1.5, durationSeconds: 2 }
      ]
    },
    ...overrides
  };
}

test("validated page data becomes the existing acquisition response contract", () => {
  const validated = validateEnvelope(successEnvelope(), videoId, requestId);

  assert.equal(validated.accepted, true);
  assert.equal(validated.result.ok, true);
  assert.deepEqual(validated.result.response.transcript, {
    language: "English",
    language_code: "en",
    is_generated: false,
    provider: "youtube-watch-page",
    provider_version: "dev-probe-1"
  });
  assert.equal(validated.result.response.timing.snippet_count, 2);
  assert.equal(validated.result.response.timing.overlapping_snippet_count, 1);
  assert.equal(validated.result.response.timing.covered_span_seconds, 3.5);
  assert.deepEqual(validated.result.response.acquisition_timing, {
    metadata_discovery_ms: 23.4,
    timed_text_fetch_ms: 100
  });
});

test("stale video or request identities are rejected", () => {
  assert.equal(
    validateEnvelope(successEnvelope(), "jNQXAC9IVRw", requestId).accepted,
    false
  );
  assert.equal(
    validateEnvelope(successEnvelope(), videoId, `${requestId}-stale`).accepted,
    false
  );
});

test("page payload cannot supply an arbitrary URL or extra fields", () => {
  const envelope = successEnvelope();
  envelope.payload.url = "https://example.com/steal-cookies";

  assert.deepEqual(validateEnvelope(envelope, videoId, requestId), {
    accepted: false,
    reason: "INVALID_PAYLOAD"
  });
});

test("invalid timing and snippet ordering are rejected", () => {
  const envelope = successEnvelope();
  envelope.payload.snippets[1].startSeconds = -1;

  assert.deepEqual(validateEnvelope(envelope, videoId, requestId), {
    accepted: false,
    reason: "INVALID_SNIPPETS"
  });
});

test("split acquisition latency must fit inside total provider latency", () => {
  const envelope = successEnvelope();
  envelope.payload.timedTextFetchMs = 200;

  assert.deepEqual(validateEnvelope(envelope, videoId, requestId), {
    accepted: false,
    reason: "INVALID_PAYLOAD"
  });
});

test("only allowlisted acquisition failures cross the page boundary", () => {
  const unavailable = {
    channel: CHANNEL,
    type: "result",
    videoId,
    requestId,
    ok: false,
    error: { code: "NO_CAPTION_TRACK" }
  };
  assert.equal(validateEnvelope(unavailable, videoId, requestId).result.errorCode,
    "NO_CAPTION_TRACK");

  unavailable.error.code = "EXPORT_COOKIES";
  assert.deepEqual(validateEnvelope(unavailable, videoId, requestId), {
    accepted: false,
    reason: "INVALID_ERROR"
  });
});
