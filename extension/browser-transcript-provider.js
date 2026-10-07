(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.BrowserTranscriptProbe = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const CHANNEL = "ytss-browser-transcript-v1";
  const MAX_SNIPPETS = 20000;
  const MAX_TEXT_LENGTH = 10000;
  const MAX_TOTAL_TEXT_LENGTH = 5_000_000;
  const ERROR_CODES = new Set([
    "NO_CAPTION_TRACK",
    "PAGE_DATA_UNAVAILABLE",
    "TIMED_TEXT_HTTP_ERROR",
    "TIMED_TEXT_PARSE_ERROR",
    "PROBE_TIMEOUT"
  ]);

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  function hasOnlyKeys(value, allowed) {
    return Object.keys(value).every((key) => allowed.has(key));
  }

  function isVideoId(value) {
    return typeof value === "string" && /^[A-Za-z0-9_-]{11}$/.test(value);
  }

  function isRequestId(value) {
    return typeof value === "string" && value.length >= 12 && value.length <= 160;
  }

  function median(values) {
    if (!values.length) return null;
    const ordered = [...values].sort((left, right) => left - right);
    const middle = Math.floor(ordered.length / 2);
    return ordered.length % 2
      ? ordered[middle]
      : (ordered[middle - 1] + ordered[middle]) / 2;
  }

  function validateSnippets(value) {
    if (!Array.isArray(value) || value.length === 0 || value.length > MAX_SNIPPETS) {
      return null;
    }
    let previousStart = -1;
    let totalTextLength = 0;
    const snippets = [];
    for (let index = 0; index < value.length; index += 1) {
      const snippet = value[index];
      if (
        !isObject(snippet) ||
        !hasOnlyKeys(snippet, new Set(["index", "text", "startSeconds", "durationSeconds"])) ||
        snippet.index !== index ||
        typeof snippet.text !== "string" ||
        snippet.text.length === 0 ||
        snippet.text.length > MAX_TEXT_LENGTH ||
        !Number.isFinite(snippet.startSeconds) ||
        snippet.startSeconds < 0 ||
        snippet.startSeconds < previousStart ||
        !Number.isFinite(snippet.durationSeconds) ||
        snippet.durationSeconds < 0
      ) {
        return null;
      }
      totalTextLength += snippet.text.length;
      if (totalTextLength > MAX_TOTAL_TEXT_LENGTH) return null;
      previousStart = snippet.startSeconds;
      snippets.push({
        index,
        text: snippet.text,
        start_seconds: snippet.startSeconds,
        duration_seconds: snippet.durationSeconds
      });
    }
    return snippets;
  }

  function timingMetrics(snippets) {
    const durations = snippets.map((snippet) => snippet.duration_seconds);
    const startGaps = snippets.slice(1).map(
      (snippet, index) => snippet.start_seconds - snippets[index].start_seconds
    );
    const overlappingSnippetCount = snippets.slice(1).filter(
      (snippet, index) =>
        snippet.start_seconds <
        snippets[index].start_seconds + snippets[index].duration_seconds
    ).length;
    const coveredSpanSeconds =
      Math.max(
        ...snippets.map((snippet) => snippet.start_seconds + snippet.duration_seconds)
      ) - snippets[0].start_seconds;
    return {
      snippet_count: snippets.length,
      median_snippet_duration_seconds: median(durations),
      median_start_gap_seconds: median(startGaps),
      overlapping_snippet_count: overlappingSnippetCount,
      covered_span_seconds: coveredSpanSeconds
    };
  }

  function validateEnvelope(value, expectedVideoId, expectedRequestId) {
    if (
      !isObject(value) ||
      !hasOnlyKeys(
        value,
        new Set(["channel", "type", "videoId", "requestId", "ok", "payload", "error"])
      ) ||
      value.channel !== CHANNEL ||
      value.type !== "result" ||
      !isVideoId(value.videoId) ||
      !isRequestId(value.requestId) ||
      value.videoId !== expectedVideoId ||
      value.requestId !== expectedRequestId ||
      typeof value.ok !== "boolean"
    ) {
      return { accepted: false, reason: "INVALID_ENVELOPE" };
    }

    if (!value.ok) {
      if (
        value.payload !== undefined ||
        !isObject(value.error) ||
        !hasOnlyKeys(value.error, new Set(["code"])) ||
        !ERROR_CODES.has(value.error.code)
      ) {
        return { accepted: false, reason: "INVALID_ERROR" };
      }
      return {
        accepted: true,
        result: {
          ok: false,
          videoId: value.videoId,
          requestId: value.requestId,
          errorCode: value.error.code
        }
      };
    }

    const payload = value.payload;
    if (
      value.error !== undefined ||
      !isObject(payload) ||
      !hasOnlyKeys(
        payload,
        new Set([
          "language",
          "languageCode",
          "isGenerated",
          "providerLatencyMs",
          "metadataDiscoveryMs",
          "timedTextFetchMs",
          "snippets"
        ])
      ) ||
      typeof payload.language !== "string" ||
      payload.language.length === 0 ||
      payload.language.length > 100 ||
      typeof payload.languageCode !== "string" ||
      payload.languageCode.length === 0 ||
      payload.languageCode.length > 35 ||
      typeof payload.isGenerated !== "boolean" ||
      !Number.isFinite(payload.providerLatencyMs) ||
      payload.providerLatencyMs < 0 ||
      !Number.isFinite(payload.metadataDiscoveryMs) ||
      payload.metadataDiscoveryMs < 0 ||
      !Number.isFinite(payload.timedTextFetchMs) ||
      payload.timedTextFetchMs < 0 ||
      payload.metadataDiscoveryMs > payload.providerLatencyMs ||
      payload.timedTextFetchMs > payload.providerLatencyMs
    ) {
      return { accepted: false, reason: "INVALID_PAYLOAD" };
    }
    const snippets = validateSnippets(payload.snippets);
    if (!snippets) return { accepted: false, reason: "INVALID_SNIPPETS" };

    return {
      accepted: true,
      result: {
        ok: true,
        response: {
          status: "ready",
          video_id: value.videoId,
          request_id: value.requestId,
          transcript: {
            language: payload.language,
            language_code: payload.languageCode,
            is_generated: payload.isGenerated,
            provider: "youtube-watch-page",
            provider_version: "dev-probe-1"
          },
          snippets,
          provider_latency_ms: payload.providerLatencyMs,
          acquisition_timing: {
            metadata_discovery_ms: payload.metadataDiscoveryMs,
            timed_text_fetch_ms: payload.timedTextFetchMs
          },
          cache_hit: false,
          coalesced: false,
          timing: timingMetrics(snippets)
        }
      }
    };
  }

  return { CHANNEL, validateEnvelope };
});
