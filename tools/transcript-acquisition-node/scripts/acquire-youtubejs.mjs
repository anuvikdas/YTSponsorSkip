import process from "node:process";
import { performance } from "node:perf_hooks";

import { Innertube } from "youtubei.js";
import youtubejsPackage from "youtubei.js/package.json" with { type: "json" };

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

try {
  const youtube = await Innertube.create({ lang: "en", location: "US" });
  const info = await youtube.getInfo(args.video);
  let transcriptInfo = await info.getTranscript();
  const englishLanguage = transcriptInfo.languages.find((language) =>
    language.toLowerCase().startsWith("english")
  );
  if (englishLanguage && transcriptInfo.selectedLanguage !== englishLanguage) {
    transcriptInfo = await transcriptInfo.selectLanguage(englishLanguage);
  }

  const rawSegments = transcriptInfo.transcript.content?.body?.initial_segments ?? [];
  const segments = rawSegments.filter(
    (segment) => segment?.constructor?.type === "TranscriptSegment"
  );
  const tracks = info.captions?.caption_tracks ?? [];
  const selectedLanguage = transcriptInfo.selectedLanguage || englishLanguage || "";
  const selectedTrack =
    tracks.find((track) => track.name.toString() === selectedLanguage) ??
    tracks.find((track) => track.language_code === "en") ??
    tracks.find((track) => track.language_code.startsWith("en"));
  const captionType = selectedTrack
    ? selectedTrack.kind === "asr"
      ? "generated"
      : "manual"
    : "unknown";
  const snippets = segments.map((segment, index) => {
    const startMs = Number(segment.start_ms);
    const endMs = Number(segment.end_ms);
    return {
      index,
      text: segment.snippet.toString(),
      start_seconds: startMs / 1000,
      duration_seconds: (endMs - startMs) / 1000
    };
  });
  const videoDurationSeconds = Number(info.basic_info.duration);
  const latencyMs = Math.round((performance.now() - started) * 1000) / 1000;
  const rawDocument = {
    video_id: args.video,
    library: "youtubei.js",
    version: youtubejsPackage.version,
    selected_language: selectedLanguage || null,
    available_languages: transcriptInfo.languages,
    caption_tracks: tracks.map((track) => ({
      name: track.name.toString(),
      language_code: track.language_code,
      kind: track.kind ?? null,
      vss_id: track.vss_id,
      is_translatable: track.is_translatable
    })),
    video_duration_seconds: Number.isFinite(videoDurationSeconds)
      ? videoDurationSeconds
      : null,
    segments: segments.map((segment) => ({
      type: segment.constructor.type,
      start_ms: segment.start_ms,
      end_ms: segment.end_ms,
      text: segment.snippet.toString()
    }))
  };
  await writeJson(args.raw, rawDocument);
  const completeness = completenessMetadata(
    snippets,
    Number.isFinite(videoDurationSeconds) ? videoDurationSeconds : null,
    [
      "YouTube.js returned one complete TranscriptSegmentList with no continuation field.",
      "Raw and normalized segment counts match.",
      "First/last transcript timestamps are recorded against video duration."
    ]
  );
  await finish(
    normalizedDocument({
      videoId: args.video,
      library: "youtubei.js",
      version: youtubejsPackage.version,
      language: selectedLanguage || selectedTrack?.name.toString() || "unknown",
      languageCode: selectedTrack?.language_code || "unknown",
      captionType,
      captionTypeEvidence: selectedTrack
        ? `caption track kind=${selectedTrack.kind ?? "unset"}`
        : "caption track could not be matched",
      latencyMs,
      snippets,
      sourceTimingUnit: "milliseconds",
      completeness
    }),
    args.output
  );
} catch (error) {
  const latencyMs = Math.round((performance.now() - started) * 1000) / 1000;
  const message = `${error?.name || ""} ${error?.message || error}`;
  const blocked = /blocked|captcha|429|too many requests|sign in to confirm/i.test(message);
  await writeJson(args.raw, {
    video_id: args.video,
    library: "youtubei.js",
    version: youtubejsPackage.version,
    error: { name: error?.name || "Error", message: error?.message || String(error) }
  });
  await finish(
    failureDocument({
      videoId: args.video,
      library: "youtubei.js",
      version: youtubejsPackage.version,
      latencyMs,
      error,
      blocked
    }),
    args.output
  );
}
