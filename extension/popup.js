const statusElement = document.querySelector("#current-status");

const labels = {
  loading: "Retrieving the transcript…",
  disabled: "Skipping is disabled.",
  "transcript-ready": "Transcript ready. Detection is not connected yet.",
  unavailable: "Skipping unavailable for this video. Playback is unaffected."
};

async function renderStatus() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    statusElement.textContent = "No active tab.";
    return;
  }
  const result = await chrome.storage.session.get(`tab-${tab.id}`);
  const state = result[`tab-${tab.id}`];
  statusElement.textContent = state ? labels[state.status] : "Open a YouTube video to begin.";
  if (state?.status === "transcript-ready") {
    statusElement.textContent += ` ${state.snippetCount} ${state.isGenerated ? "generated" : "manual"} caption snippets.`;
  }
  if (state?.status === "unavailable" && state.reason) {
    statusElement.textContent += ` Reason: ${state.reason}.`;
  }
}

document.querySelector("#open-options").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

renderStatus();
