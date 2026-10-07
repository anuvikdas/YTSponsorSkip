importScripts("defaults.js");

const controllersByTab = new Map();
const requestMetadataByTab = new Map();

function stateKey(tabId) {
  return `tab-${tabId}`;
}

function transcriptKey(tabId) {
  return `transcript-${tabId}`;
}

async function saveState(tabId, state) {
  await chrome.storage.session.set({ [stateKey(tabId)]: state });
}

function isCurrentRequest(tabId, controller) {
  return controllersByTab.get(tabId) === controller && !controller.signal.aborted;
}

function clearCurrentRequest(tabId, controller) {
  if (!isCurrentRequest(tabId, controller)) return;
  const metadata = requestMetadataByTab.get(tabId);
  clearTimeout(metadata?.timeoutId);
  requestMetadataByTab.delete(tabId);
  controllersByTab.delete(tabId);
}

function cancelTabRequest(tabId) {
  controllersByTab.get(tabId)?.abort();
  clearTimeout(requestMetadataByTab.get(tabId)?.timeoutId);
  controllersByTab.delete(tabId);
  requestMetadataByTab.delete(tabId);
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
  if (!sender.tab?.id) {
    return undefined;
  }

  const tabId = sender.tab.id;
  if (message.type === "video-changed") {
    cancelTabRequest(tabId);
    chrome.storage.session.remove(transcriptKey(tabId));
    const controller = new AbortController();
    controllersByTab.set(tabId, controller);
    requestMetadataByTab.set(tabId, {
      videoId: message.videoId,
      requestId: message.requestId,
      mode: message.acquisitionMode,
      startedAtMs: Date.now(),
      timeoutId: null
    });
    if (message.acquisitionMode === "browser-probe") {
      beginBrowserTranscriptProbe(tabId, message.videoId, message.requestId, controller);
    } else {
      acquireTranscript(tabId, message.videoId, message.requestId, controller);
    }
    return undefined;
  }
  if (message.type === "browser-transcript-result") {
    handleBrowserTranscriptResult(tabId, message);
  }
  return undefined;
});

async function beginBrowserTranscriptProbe(tabId, videoId, requestId, controller) {
  const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  if (!isCurrentRequest(tabId, controller)) return;
  if (!settings.enabled) {
    await notifyCurrentRequest(tabId, { status: "disabled", videoId, requestId }, controller);
    clearCurrentRequest(tabId, controller);
    return;
  }
  if (!settings.developmentBrowserAcquisition) {
    await acquireTranscript(tabId, videoId, requestId, controller);
    return;
  }
  await notifyCurrentRequest(
    tabId,
    { status: "loading", videoId, requestId, provider: "youtube-watch-page" },
    controller
  );
  if (!isCurrentRequest(tabId, controller)) return;
  const metadata = requestMetadataByTab.get(tabId);
  metadata.timeoutId = setTimeout(async () => {
    if (!isCurrentRequest(tabId, controller)) return;
    await notifyCurrentRequest(
      tabId,
      { status: "unavailable", videoId, requestId, reason: "PROBE_TIMEOUT" },
      controller
    );
    clearCurrentRequest(tabId, controller);
  }, 10000);
}

async function handleBrowserTranscriptResult(tabId, message) {
  const controller = controllersByTab.get(tabId);
  const metadata = requestMetadataByTab.get(tabId);
  if (
    !controller ||
    !metadata ||
    metadata.mode !== "browser-probe" ||
    metadata.videoId !== message.videoId ||
    metadata.requestId !== message.requestId ||
    !isCurrentRequest(tabId, controller)
  ) {
    return;
  }

  const result = message.result;
  if (!result?.ok) {
    await notifyCurrentRequest(
      tabId,
      {
        status: "unavailable",
        videoId: message.videoId,
        requestId: message.requestId,
        reason: result?.errorCode || "INVALID_BROWSER_RESULT"
      },
      controller
    );
    clearCurrentRequest(tabId, controller);
    return;
  }

  const response = result.response;
  if (
    response?.video_id !== message.videoId ||
    response?.request_id !== message.requestId ||
    !Array.isArray(response?.snippets) ||
    response.snippets.length !== response?.timing?.snippet_count
  ) {
    await notifyCurrentRequest(
      tabId,
      {
        status: "unavailable",
        videoId: message.videoId,
        requestId: message.requestId,
        reason: "INVALID_BROWSER_RESULT"
      },
      controller
    );
    clearCurrentRequest(tabId, controller);
    return;
  }

  let storedForInspection = true;
  try {
    await chrome.storage.session.set({ [transcriptKey(tabId)]: response });
  } catch (_) {
    storedForInspection = false;
  }
  await notifyCurrentRequest(
    tabId,
    {
      status: "transcript-ready",
      videoId: message.videoId,
      requestId: message.requestId,
      languageCode: response.transcript.language_code,
      isGenerated: response.transcript.is_generated,
      snippetCount: response.timing.snippet_count,
      provider: response.transcript.provider,
      providerLatencyMs: response.provider_latency_ms,
      metadataDiscoveryMs: response.acquisition_timing.metadata_discovery_ms,
      timedTextFetchMs: response.acquisition_timing.timed_text_fetch_ms,
      requestToReadyMs: Date.now() - metadata.startedAtMs,
      storedForInspection
    },
    controller
  );
  clearCurrentRequest(tabId, controller);
}

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
    clearCurrentRequest(tabId, controller);
  }
}

chrome.tabs.onRemoved.addListener((tabId) => {
  cancelTabRequest(tabId);
  chrome.storage.session.remove([stateKey(tabId), transcriptKey(tabId)]);
});
