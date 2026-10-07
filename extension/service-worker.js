importScripts("defaults.js");

const controllersByTab = new Map();

function stateKey(tabId) {
  return `tab-${tabId}`;
}

async function saveState(tabId, state) {
  await chrome.storage.session.set({ [stateKey(tabId)]: state });
}

function isCurrentRequest(tabId, controller) {
  return controllersByTab.get(tabId) === controller && !controller.signal.aborted;
}

async function notifyCurrentRequest(tabId, state, controller) {
  if (!isCurrentRequest(tabId, controller)) return;
  await saveState(tabId, state);
  if (!isCurrentRequest(tabId, controller)) return;
  try {
    await chrome.tabs.sendMessage(tabId, { type: "acquisition-status", state });
  } catch (_) {
    // The tab may have navigated before the response arrived.
  }
}

chrome.runtime.onMessage.addListener((message, sender) => {
  if (message.type !== "video-changed" || !sender.tab?.id) {
    return undefined;
  }

  const tabId = sender.tab.id;
  controllersByTab.get(tabId)?.abort();
  const controller = new AbortController();
  controllersByTab.set(tabId, controller);
  acquireTranscript(tabId, message.videoId, message.requestId, controller);
  return undefined;
});

async function acquireTranscript(tabId, videoId, requestId, controller) {
  try {
    const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
    if (!isCurrentRequest(tabId, controller)) return;
    if (!settings.enabled) {
      await notifyCurrentRequest(
        tabId,
        { status: "disabled", videoId, requestId },
        controller
      );
      return;
    }

    await notifyCurrentRequest(tabId, { status: "loading", videoId, requestId }, controller);
    const url = new URL(
      `/api/v1/transcripts/${encodeURIComponent(videoId)}`,
      settings.backendUrl
    );
    url.searchParams.append("languages", "en");
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { "X-Request-ID": requestId }
    });
    const body = await response.json();
    if (!isCurrentRequest(tabId, controller)) return;

    if (!response.ok) {
      await notifyCurrentRequest(
        tabId,
        {
          status: "unavailable",
          videoId,
          requestId,
          reason: body.error?.code || `HTTP_${response.status}`
        },
        controller
      );
      return;
    }

    await notifyCurrentRequest(
      tabId,
      {
        status: "transcript-ready",
        videoId,
        requestId,
        languageCode: body.transcript.language_code,
        isGenerated: body.transcript.is_generated,
        snippetCount: body.timing.snippet_count
      },
      controller
    );
  } catch (error) {
    if (error.name !== "AbortError") {
      await notifyCurrentRequest(
        tabId,
        {
          status: "unavailable",
          videoId,
          requestId,
          reason: "BACKEND_UNREACHABLE"
        },
        controller
      );
    }
  } finally {
    if (controllersByTab.get(tabId) === controller) {
      controllersByTab.delete(tabId);
    }
  }
}

chrome.tabs.onRemoved.addListener((tabId) => {
  controllersByTab.get(tabId)?.abort();
  controllersByTab.delete(tabId);
  chrome.storage.session.remove(stateKey(tabId));
});
