let currentVideoId = null;
let currentRequestId = null;
let currentConfigurationKey = null;
let refreshGeneration = 0;
let previewActive = false;
let experimentalActive = false;
let activeSource = null;
let activeSensitivity = null;
let lastUrl = location.href;
let notificationTimer = null;
let developmentFixtureTimer = null;
let browserProbeTimer = null;
let observedVideo = null;
let validatedDetectorVersion = null;
let detectorVerifiedAt = 0;

function videoIsLive() {
  const video = document.querySelector("video");
  const badge = document.querySelector(".ytp-live-badge");
  // YouTube keeps a hidden Live button on prerecorded videos too.
  const style = badge ? getComputedStyle(badge) : null;
  return video?.duration === Infinity || Boolean(badge && !badge.disabled &&
    style.display !== "none" && style.visibility !== "hidden" && badge.offsetParent !== null);
}

const playbackController = new PlaybackController({
  onSkip: showSkipNotification,
  onUndo: showUndoNotification,
  canSeek: () => videoIdFromLocation() === currentVideoId &&
    !document.querySelector(".ad-showing, .ad-interrupting") && !videoIsLive() &&
    (!experimentalActive || (validatedDetectorVersion && Date.now() - detectorVerifiedAt < 15000))
});

function videoIdFromLocation() {
  const url = new URL(location.href);
  const candidate = url.pathname === "/watch" ? url.searchParams.get("v") : null;
  return candidate && /^[A-Za-z0-9_-]{11}$/.test(candidate) ? candidate : null;
}

function makeRequestId(videoId) {
  return `${videoId}-${Date.now()}-${crypto.randomUUID()}`;
}

async function checkForVideoChange() {
  const generation = ++refreshGeneration;
  const videoId = videoIdFromLocation();
  if (videoId !== currentVideoId) {
    currentVideoId = videoId;
    currentRequestId = null;
    currentConfigurationKey = null;
    previewActive = false;
    experimentalActive = false;
    clearTimeout(developmentFixtureTimer);
    clearTimeout(browserProbeTimer);
    playbackController.beginVideo(videoId, null);
    removeNotification();
    chrome.runtime.sendMessage({ type: "video-cleared", videoId });
  }
  const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  if (generation !== refreshGeneration || videoId !== currentVideoId) return;
  const configurationKey = JSON.stringify([
    settings.enabled, settings.previewDetectedPromotions, settings.previewTranscriptSource,
    settings.experimentalAutoSkip, settings.detectorVariant,
    settings.sensitivity, settings.developmentFixtures, settings.developmentBrowserAcquisition,
    settings.backendUrl, videoIsLive()
  ]);
  if (configurationKey === currentConfigurationKey) return;
  currentConfigurationKey = configurationKey;
  currentRequestId = videoId ? makeRequestId(videoId) : null;
  previewActive = settings.previewDetectedPromotions === true;
  experimentalActive = settings.enabled && settings.experimentalAutoSkip === true && !previewActive &&
    !settings.developmentFixtures && !settings.developmentBrowserAcquisition &&
    settings.sensitivity === "conservative" && settings.detectorVariant === "contextual_v1";
  activeSource = settings.previewTranscriptSource;
  activeSensitivity = settings.sensitivity;
  clearTimeout(developmentFixtureTimer);
  clearTimeout(browserProbeTimer);
  playbackController.beginVideo(currentVideoId, currentRequestId);
  validatedDetectorVersion = null;
  attachCurrentVideo();
  removeNotification();
  beginAcquisition(videoId, currentRequestId, settings);
  if (videoId && !previewActive && !experimentalActive && !settings.developmentBrowserAcquisition) {
    scheduleDevelopmentFixture(videoId, currentRequestId, settings);
  }
}

function beginAcquisition(videoId, requestId, settings) {
  if (!videoId) {
    chrome.runtime.sendMessage({ type: "video-changed", videoId: null, requestId: null });
    return;
  }
  const browserProbe = settings.developmentBrowserAcquisition === true;
  const fixture = settings.developmentFixtures === true;
  const preview = settings.previewDetectedPromotions === true;
  const auto = settings.experimentalAutoSkip === true;
  const acquisitionMode = !settings.enabled ? "disabled" : videoIsLive() ? "unsupported"
    : (preview && auto) || ((preview || auto) && (browserProbe || fixture)) ? "conflict"
      : auto ? "experimental" : preview ? "preview" : browserProbe ? "browser-probe"
        : fixture ? "manual-fixture" : "disabled";
  chrome.runtime.sendMessage({
    type: "video-changed",
    videoId,
    requestId,
    acquisitionMode,
    previewSource: settings.previewTranscriptSource,
    sensitivity: settings.sensitivity,
    backendUrl: settings.backendUrl
  });
  if (!browserProbe || preview || auto || !settings.enabled) return;
  document.dispatchEvent(
    new CustomEvent("ytss-browser-transcript-request", {
      detail: { videoId, requestId }
    })
  );
  browserProbeTimer = setTimeout(() => {
    if (videoId !== currentVideoId || requestId !== currentRequestId) return;
    chrome.runtime.sendMessage({
      type: "browser-transcript-result",
      videoId,
      requestId,
      result: { ok: false, errorCode: "PROBE_TIMEOUT" }
    });
  }, 8000);
}

window.addEventListener("message", (event) => {
  if (event.source !== window || event.origin !== location.origin) return;
  const validated = BrowserTranscriptProbe.validateEnvelope(
    event.data,
    currentVideoId,
    currentRequestId
  );
  if (!validated.accepted) return;
  clearTimeout(browserProbeTimer);
  chrome.runtime.sendMessage({
    type: "browser-transcript-result",
    videoId: currentVideoId,
    requestId: currentRequestId,
    result: validated.result
  });
});

function removeNotification() {
  clearTimeout(notificationTimer);
  document.querySelector("#ytss-notification")?.remove();
}

async function showUnavailable(state) {
  await showNotification(
    `YTSponsorSkip unavailable: ${state.reason.replaceAll("_", " ").toLowerCase()}`
  );
}

async function showSkipNotification(event) {
  const seconds = Math.max(0, Math.round(event.endSeconds - event.preSkipTime));
  const label =
    event.source === "manual-tune-fixture"
      ? "Skipped a manual development fixture"
      : "Skipped a promotional interval";
  await showNotification(`${experimentalActive ? "Experimental: " : ""}${label} (${seconds}s).`, {
    actionLabel: "Undo",
    action: () => playbackController.undoLastSkip(),
    videoId: event.videoId, requestId: event.requestId
  });
}

async function showUndoNotification() {
  await showNotification("Skip undone. This interval is suppressed until you leave it.");
}

async function showNotification(text, { actionLabel = null, action = null,
  videoId = currentVideoId, requestId = currentRequestId } = {}) {
  const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  if (videoId !== currentVideoId || requestId !== currentRequestId) return;
  // An automatic skip always offers Undo, even when optional status notices are off.
  if (!settings.showNotifications && !action) return;

  removeNotification();
  const notice = document.createElement("div");
  notice.id = "ytss-notification";
  const message = document.createElement("span");
  message.textContent = text;
  notice.appendChild(message);
  if (actionLabel && action) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = actionLabel;
    Object.assign(button.style, {
      marginLeft: "12px",
      border: "1px solid rgba(255, 255, 255, 0.7)",
      borderRadius: "6px",
      padding: "4px 9px",
      color: "#fff",
      background: "transparent",
      cursor: "pointer",
      font: "600 13px system-ui, sans-serif"
    });
    button.addEventListener("click", () => {
      if (action()) removeNotification();
    });
    notice.appendChild(button);
  }
  Object.assign(notice.style, {
    position: "fixed",
    right: "20px",
    bottom: "72px",
    zIndex: "2147483647",
    padding: "10px 14px",
    borderRadius: "8px",
    color: "#fff",
    background: "rgba(24, 24, 27, 0.94)",
    font: "13px system-ui, sans-serif",
    display: "flex",
    alignItems: "center",
    boxShadow: "0 8px 28px rgba(0, 0, 0, 0.3)"
  });
  document.body.appendChild(notice);
  notificationTimer = setTimeout(removeNotification, 6000);
}

function attachCurrentVideo() {
  const video = document.querySelector("video");
  if (observedVideo !== video) {
    observedVideo?.removeEventListener("durationchange", checkForVideoChange);
    observedVideo = video;
    video?.addEventListener("durationchange", checkForVideoChange);
  }
  playbackController.attachVideo(video);
}

async function scheduleDevelopmentFixture(videoId, requestId, settings) {
  if (
    !settings.enabled ||
    settings.previewDetectedPromotions ||
    settings.experimentalAutoSkip ||
    !settings.developmentFixtures ||
    videoId !== currentVideoId ||
    requestId !== currentRequestId
  ) {
    return;
  }
  const fixture = DEVELOPMENT_PLAYBACK_FIXTURES[videoId];
  if (!fixture) return;
  developmentFixtureTimer = setTimeout(() => {
    playbackController.setIntervals({
      videoId,
      requestId,
      intervals: fixture.intervals,
      source: "manual-tune-fixture"
    });
  }, DEVELOPMENT_FIXTURE_DELAY_MS);
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "undo-last-skip") {
    const current = message.videoId === currentVideoId && message.requestId === currentRequestId;
    sendResponse?.({ undone: Boolean(current && experimentalActive && playbackController.undoLastSkip()) });
    return;
  }
  if (message.type === "acquisition-status") {
    const state = message.state;
    if (state.videoId !== currentVideoId || state.requestId !== currentRequestId) return;
    if (state.status === "unavailable" && !previewActive) {
      playbackController.beginVideo(currentVideoId, currentRequestId);
      showUnavailable(state);
    }
    return;
  }
  if (message.type === "promotion-intervals") {
    if (previewActive) return;
    if (message.source !== "manual-tune-fixture" && (
      !experimentalActive || message.mode !== "conservative" ||
      message.transcriptSource !== activeSource || activeSensitivity !== "conservative" ||
      !message.detectorVersion?.startsWith("contextual-v1-sha256:")
    )) return;
    if (experimentalActive) {
      validatedDetectorVersion = message.detectorVersion;
      detectorVerifiedAt = Date.now();
    }
    playbackController.setIntervals(message);
  }
});

// Read-only health/version checks never request another transcript. Fail closed until reload
// if the backend is restarted with a different detector, or cannot be revalidated.
async function verifyActiveDetector() {
  if (!experimentalActive || !validatedDetectorVersion) return;
  const videoId = currentVideoId, requestId = currentRequestId;
  const detectorVersion = validatedDetectorVersion;
  let result;
  try {
    result = await chrome.runtime.sendMessage({type:"verify-detector", detectorVersion});
  } catch (_) { result = null; }
  if (videoId !== currentVideoId || requestId !== currentRequestId || !experimentalActive) return;
  if (result?.valid) { detectorVerifiedAt = Date.now(); return; }
  experimentalActive = false;
  validatedDetectorVersion = null;
  playbackController.beginVideo(videoId, requestId);
  removeNotification();
  chrome.runtime.sendMessage({type:"detector-invalidated", videoId, requestId});
}
setInterval(verifyActiveDetector, 10000);

document.addEventListener("yt-navigate-finish", checkForVideoChange);
window.addEventListener("popstate", checkForVideoChange);
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "sync" && Object.keys(changes).some((key) => key in DEFAULT_SETTINGS)) {
    currentRequestId = null;
    currentConfigurationKey = null;
    previewActive = false;
    experimentalActive = false;
    clearTimeout(developmentFixtureTimer);
    clearTimeout(browserProbeTimer);
    playbackController.beginVideo(currentVideoId, null);
    chrome.runtime.sendMessage({ type: "video-cleared", videoId: currentVideoId });
    checkForVideoChange();
  }
});
new MutationObserver(attachCurrentVideo).observe(document.documentElement, {
  childList: true,
  subtree: true
});
setInterval(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    checkForVideoChange();
  }
}, 1000);
attachCurrentVideo();
checkForVideoChange();
