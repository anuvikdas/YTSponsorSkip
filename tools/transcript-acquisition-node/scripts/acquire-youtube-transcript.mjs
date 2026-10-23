import process from "node:process";
import { performance } from "node:perf_hooks";

import { fetchTranscript } from "youtube-transcript";
import transcriptPackage from "youtube-transcript/package.json" with { type: "json" };

import {
  completenessMetadata,
  failureDocument,
  finish,
  normalizedDocument,
  parseArguments,
  writeJson
} from "./common.mjs";

const args = parseArguments(process.argv.slice(2));
const started = performance.now();
const captures = [];

async function instrumentedFetch(input, init) {
  const response = await fetch(input, init);
  const url = typeof input === "string" ? input : input.url;
  const clone = response.clone();
  const body = await clone.text();
  captures.push({ url, status: response.status, body });
  return response;
}

try {
  const lines = await fetchTranscript(args.video, {
    lang: "en",
    fetch: instrumentedFetch
  });
  const transcriptCapture = captures.find(
    (capture) => capture.url.includes("timedtext") || /<(?:timedtext|transcript)/.test(capture.body)
  );
  const playerCapture = captures.find((capture) => {
    try {
      return Boolean(JSON.parse(capture.body)?.captions?.playerCaptionsTracklistRenderer);
    } catch {
      return false;
    }
  });
  let playerResponse = null;
  if (playerCapture) playerResponse = JSON.parse(playerCapture.body);
  const tracks = playerResponse?.captions?.playerCaptionsTracklistRenderer?.captionTracks ?? [];
  const selectedTrack = tracks.find((track) => track.languageCode === "en");
  const rawBody = transcriptCapture?.body ?? "";
  const sourceTimingUnit = /<p\s+t="\d+"\s+d="\d+"/.test(rawBody)
    ? "milliseconds"
    : /<text\s+start="/.test(rawBody)
      ? "seconds"
      : "unknown";
  if (sourceTimingUnit === "unknown" && lines.length > 0) {
    throw new Error("Transcript timing units could not be established from the raw response.");
  }
  const divisor = sourceTimingUnit === "milliseconds" ? 1000 : 1;
  const snippets = lines.map((line, index) => ({
    index,
    text: line.text,
    start_seconds: line.offset / divisor,
    duration_seconds: line.duration / divisor
  }));
  const videoDurationSeconds = Number(playerResponse?.videoDetails?.lengthSeconds);
  const captionType = selectedTrack
    ? selectedTrack.kind === "asr"
      ? "generated"
      : "manual"
    : "unknown";
  const latencyMs = Math.round((performance.now() - started) * 1000) / 1000;
  await writeJson(args.raw, {
    video_id: args.video,
    library: "youtube-transcript",
    version: transcriptPackage.version,
    selected_track: selectedTrack
      ? {
          language_code: selectedTrack.languageCode,
          name: selectedTrack.name?.simpleText ?? null,
          kind: selectedTrack.kind ?? null,
          vss_id: selectedTrack.vssId ?? null
        }
      : null,
    source_timing_unit: sourceTimingUnit,
    video_duration_seconds: Number.isFinite(videoDurationSeconds)
      ? videoDurationSeconds
      : null,
    library_output: lines,
    network_responses: captures
  });
  const completeness = completenessMetadata(
    snippets,
    Number.isFinite(videoDurationSeconds) ? videoDurationSeconds : null,
    [
      "The library consumed one timed-text response; the protocol exposed no pagination.",
      "Raw library output and normalized snippet counts match.",
      "The raw XML format was inspected before converting timing units."
    ]
  );
  await finish(
    normalizedDocument({
      videoId: args.video,
      library: "youtube-transcript",
      version: transcriptPackage.version,
      language: selectedTrack?.name?.simpleText || "English",
      languageCode: selectedTrack?.languageCode || lines[0]?.lang || "en",
      captionType,
      captionTypeEvidence: selectedTrack
        ? `caption track kind=${selectedTrack.kind ?? "unset"}`
        : "caption track metadata unavailable",
      latencyMs,
      snippets,
      sourceTimingUnit,
      completeness
    }),
    args.output
  );
} catch (error) {
  const latencyMs = Math.round((performance.now() - started) * 1000) / 1000;
  const message = `${error?.name || ""} ${error?.message || error}`;
  const blocked = /TooManyRequest|blocked|captcha|429|too many requests|sign in to confirm/i.test(
    message
  );
  await writeJson(args.raw, {
    video_id: args.video,
    library: "youtube-transcript",
    version: transcriptPackage.version,
    error: { name: error?.name || "Error", message: error?.message || String(error) },
    network_responses: captures
  });
  await finish(
    failureDocument({
      videoId: args.video,
      library: "youtube-transcript",
      version: transcriptPackage.version,
      latencyMs,
      error,
      blocked
    }),
    args.output
  );
}
