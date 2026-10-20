const statusElement = document.querySelector("#current-status");
const previewBanner = document.querySelector("#preview-banner");
const previewDetails = document.querySelector("#preview-details");
const previewSource = document.querySelector("#preview-source");
const previewIntervals = document.querySelector("#preview-intervals");
const previewTiming = document.querySelector("#preview-timing");

function timestamp(seconds) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${(seconds % 60).toFixed(1).padStart(4, "0")}`;
}

const labels = {
  loading: "Retrieving the transcript…",
  disabled: "Skipping is disabled.",
  "transcript-ready": "Transcript ready. Detection is not connected yet.",
  unavailable: "Skipping unavailable for this video. Playback is unaffected."
};

async function renderStatus() {
  const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  previewBanner.hidden = !settings.previewDetectedPromotions;
  previewDetails.hidden = true;
  previewIntervals.replaceChildren();
  if (!tab?.id) {
    statusElement.textContent = "No active tab.";
    return;
  }
  const result = await chrome.storage.session.get(`tab-${tab.id}`);
  const state = result[`tab-${tab.id}`];
  if (settings.previewDetectedPromotions) {
    const sourceName = state?.source === "supadata" ? "Supadata native captions"
      : state?.source === "saved" ? "Saved reviewed-tune transcript" : "Source pending";
    if (!state || state.status === "loading") {
      statusElement.textContent = `Detecting promotions… ${sourceName}. Playback continues.`;
    } else if (state.status === "unsupported") {
      statusElement.textContent = "Unsupported page or video. Open a standard YouTube watch URL.";
    } else if (state.status === "unavailable") {
      statusElement.textContent = `Preview unavailable (${state.reason || "UNKNOWN_ERROR"}). Playback continues normally.`;
    } else if (state.status === "no-promotions" || state.status === "predictions-available") {
      statusElement.textContent = state.status === "no-promotions"
        ? "No promotions detected by the current rules."
        : `${state.intervals.length} predicted promotional interval(s).`;
      previewDetails.hidden = false;
      previewSource.textContent = `${sourceName} · ${state.mode} · heuristic rules`;
      previewTiming.textContent = state.timingProvenance?.startsWith("derived_")
        ? "Cue ends are derived analysis spans, not exact speech boundaries."
        : "Caption durations do not define exact promotional boundaries.";
      for (const interval of state.intervals) {
        const item = document.createElement("li");
        item.textContent = `${timestamp(interval.startSeconds)}–${timestamp(interval.endSeconds)}` +
          (interval.autoSkipEligible ? "" : " · ≤3 s, ineligible for automatic skipping");
        previewIntervals.appendChild(item);
      }
    } else {
      statusElement.textContent = "Preview is off or waiting for this video.";
    }
    return;
  }
  statusElement.textContent = state ? labels[state.status] : "Open a YouTube video to begin.";
  if (state?.status === "transcript-ready") {
    const captionType = state.isGenerated === true
      ? "generated"
      : state.isGenerated === false ? "manual" : "unknown-type";
    statusElement.textContent += ` ${state.snippetCount} ${captionType} caption snippets.`;
    if (state.provider === "youtube-watch-page") {
      statusElement.textContent += ` Browser probe: ${Math.round(state.requestToReadyMs)} ms ready (${Math.round(state.metadataDiscoveryMs)} ms metadata, ${Math.round(state.timedTextFetchMs)} ms timed text).`;
    }
  }
  if (state?.status === "unavailable" && state.reason) {
    statusElement.textContent += ` Reason: ${state.reason}.`;
  }
}

document.querySelector("#open-options").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

renderStatus();
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "session" || area === "sync") renderStatus();
});
