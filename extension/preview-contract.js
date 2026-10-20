function validatePreviewResponse(body, expected) {
  if (
    !body || body.status !== "ready" ||
    body.video_id !== expected.videoId ||
    body.request_id !== expected.requestId ||
    body.mode !== expected.mode ||
    body.transcript_source !== expected.source ||
    typeof body.detector_version !== "string" ||
    typeof body.transcript_provider !== "string" ||
    !Array.isArray(body.intervals)
  ) return null;
  const intervals = [];
  for (const item of body.intervals) {
    const start = item?.start_seconds;
    const end = item?.end_seconds;
    if (
      typeof start !== "number" || !Number.isFinite(start) || start < 0 ||
      typeof end !== "number" || !Number.isFinite(end) || end <= start
    ) return null;
    intervals.push({
      startSeconds: start,
      endSeconds: end,
      autoSkipEligible: end - start > 3
    });
  }
  return {
    status: intervals.length ? "predictions-available" : "no-promotions",
    videoId: expected.videoId,
    requestId: expected.requestId,
    mode: expected.mode,
    source: expected.source,
    transcriptProvider: body.transcript_provider,
    timingProvenance: body.timing_provenance,
    detectorVersion: body.detector_version,
    intervals,
    transcriptCacheHit: body.transcript_cache_hit === true,
    detectionCacheHit: body.detection_cache_hit === true,
    totalLatencyMs: body.total_latency_ms
  };
}

function localBackendUrl(value) {
  try {
    const url = new URL(value);
    if (
      url.protocol !== "http:" ||
      !["127.0.0.1", "localhost"].includes(url.hostname) ||
      url.port !== "8000" ||
      (url.pathname !== "/" && url.pathname !== "") ||
      url.search || url.hash || url.username || url.password
    ) return null;
    return url.origin;
  } catch (_) {
    return null;
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { validatePreviewResponse, localBackendUrl };
}
