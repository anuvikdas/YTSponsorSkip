import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

export function parseArguments(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) throw new Error(`Unexpected argument: ${token}`);
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`Missing value for ${token}`);
    values[token.slice(2)] = value;
    index += 1;
  }
  if (!values.video) throw new Error("--video is required");
  return values;
}

export async function writeJson(filePath, value) {
  if (!filePath) return;
  await mkdir(path.dirname(filePath), { recursive: true });
  await writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

export function overlapCount(snippets) {
  let overlaps = 0;
  for (let index = 1; index < snippets.length; index += 1) {
    const previous = snippets[index - 1];
    if (snippets[index].start_seconds < previous.start_seconds + previous.duration_seconds) {
      overlaps += 1;
    }
  }
  return overlaps;
}

export function completenessMetadata(snippets, videoDurationSeconds, evidence) {
  const first = snippets.at(0);
  const last = snippets.at(-1);
  const lastEnd = last ? last.start_seconds + last.duration_seconds : null;
  return {
    raw_segment_count: snippets.length,
    normalized_snippet_count: snippets.length,
    first_start_seconds: first?.start_seconds ?? null,
    last_end_seconds: lastEnd,
    video_duration_seconds: videoDurationSeconds,
    trailing_gap_seconds:
      lastEnd !== null && Number.isFinite(videoDurationSeconds)
        ? Math.max(0, videoDurationSeconds - lastEnd)
        : null,
    overlapping_adjacent_snippets: overlapCount(snippets),
    pagination_required: false,
    truncation_status: snippets.length > 0 ? "no_evidence_detected" : "empty",
    evidence
  };
}

export function normalizedDocument({
  videoId,
  library,
  version,
  language,
  languageCode,
  captionType,
  captionTypeEvidence,
  latencyMs,
  snippets,
  sourceTimingUnit,
  completeness
}) {
  return {
    schema_version: 1,
    status: "ready",
    video_id: videoId,
    acquired_at: new Date().toISOString(),
    environment: {
      kind: "local-node",
      node_version: process.version,
      browser_context: false
    },
    source: {
      library,
      version,
      credentials_used: false,
      cookies_used: false,
      transcript_panel_opened: false
    },
    transcript: {
      language,
      language_code: languageCode,
      is_generated:
        captionType === "generated" ? true : captionType === "manual" ? false : null,
      caption_type: captionType,
      caption_type_evidence: captionTypeEvidence,
      provider: library,
      provider_version: version
    },
    acquisition_latency_ms: latencyMs,
    timing: {
      source_unit: sourceTimingUnit,
      normalized_unit: "seconds",
      duration_available: snippets.every((snippet) => Number.isFinite(snippet.duration_seconds))
    },
    completeness,
    snippets
  };
}

export function failureDocument({ videoId, library, version, latencyMs, error, blocked }) {
  return {
    schema_version: 1,
    status: "unavailable",
    video_id: videoId,
    acquired_at: new Date().toISOString(),
    environment: {
      kind: "local-node",
      node_version: process.version,
      browser_context: false
    },
    source: {
      library,
      version,
      credentials_used: false,
      cookies_used: false,
      transcript_panel_opened: false
    },
    acquisition_latency_ms: latencyMs,
    error: {
      code: blocked ? "ACCESS_BLOCKED" : error?.name || "ACQUISITION_FAILED",
      message: error?.message || String(error),
      blocked
    }
  };
}

export async function finish(document, outputPath) {
  await writeJson(outputPath, document);
  process.stdout.write(`${JSON.stringify(document)}\n`);
  if (document.status !== "ready") process.exitCode = document.error.blocked ? 2 : 1;
}
