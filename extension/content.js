let currentVideoId = null;
let currentRequestId = null;
let lastUrl = location.href;
let notificationTimer = null;
let developmentFixtureTimer = null;

const playbackController = new PlaybackController({
  onSkip: showSkipNotification,
  onUndo: showUndoNotification
});

function videoIdFromLocation() {
  const url = new URL(location.href);
  return url.pathname === "/watch" ? url.searchParams.get("v") : null;
}

function makeRequestId(videoId) {
  return `${videoId}-${Date.now()}-${crypto.randomUUID()}`;
}

function checkForVideoChange() {
  const videoId = videoIdFromLocation();
  if (videoId === currentVideoId) return;
  currentVideoId = videoId;
  currentRequestId = videoId ? makeRequestId(videoId) : null;
  clearTimeout(developmentFixtureTimer);
  playbackController.beginVideo(currentVideoId, currentRequestId);
  attachCurrentVideo();
  removeNotification();
  if (videoId) {
    chrome.runtime.sendMessage({
      type: "video-changed",
      videoId,
      requestId: currentRequestId
    });
    scheduleDevelopmentFixture(videoId, currentRequestId);
  }
}

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
  await showNotification(`${label} (${seconds}s).`, {
    actionLabel: "Undo",
    action: () => playbackController.undoLastSkip()
  });
}

async function showUndoNotification() {
  await showNotification("Skip undone. This interval is suppressed until you leave it.");
}

async function showNotification(text, { actionLabel = null, action = null } = {}) {
  const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  if (!settings.showNotifications) return;

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
  playbackController.attachVideo(document.querySelector("video"));
}

async function scheduleDevelopmentFixture(videoId, requestId) {
  const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  if (
    !settings.enabled ||
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

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "acquisition-status") {
    const state = message.state;
    if (state.videoId !== currentVideoId || state.requestId !== currentRequestId) return;
    if (state.status === "unavailable") showUnavailable(state);
    return;
  }
  if (message.type === "promotion-intervals") {
    playbackController.setIntervals(message);
  }
});

document.addEventListener("yt-navigate-finish", checkForVideoChange);
window.addEventListener("popstate", checkForVideoChange);
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
