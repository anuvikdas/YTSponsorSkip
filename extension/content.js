let currentVideoId = null;
let currentRequestId = null;
let lastUrl = location.href;
let notificationTimer = null;

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
  removeNotification();
  if (videoId) {
    chrome.runtime.sendMessage({
      type: "video-changed",
      videoId,
      requestId: currentRequestId
    });
  }
}

function removeNotification() {
  clearTimeout(notificationTimer);
  document.querySelector("#ytss-notification")?.remove();
}

async function showUnavailable(state) {
  const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  if (!settings.showNotifications) return;

  removeNotification();
  const notice = document.createElement("div");
  notice.id = "ytss-notification";
  notice.textContent = `YTSponsorSkip unavailable: ${state.reason.replaceAll("_", " ").toLowerCase()}`;
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
    boxShadow: "0 8px 28px rgba(0, 0, 0, 0.3)"
  });
  document.body.appendChild(notice);
  notificationTimer = setTimeout(removeNotification, 6000);
}

chrome.runtime.onMessage.addListener((message) => {
  if (message.type !== "acquisition-status") return;
  const state = message.state;
  if (state.videoId !== currentVideoId || state.requestId !== currentRequestId) return;
  if (state.status === "unavailable") showUnavailable(state);
});

document.addEventListener("yt-navigate-finish", checkForVideoChange);
window.addEventListener("popstate", checkForVideoChange);
setInterval(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    checkForVideoChange();
  }
}, 1000);
checkForVideoChange();
