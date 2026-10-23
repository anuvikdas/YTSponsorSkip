importScripts("defaults.js", "preview-contract.js");

const controllersByTab = new Map();
const requestMetadataByTab = new Map();
const generationsByTab = new Map();
const stateWritesByTab = new Map();

function stateKey(tabId) {
  return `tab-${tabId}`;
}

function transcriptKey(tabId) {
  return `transcript-${tabId}`;
}

async function saveState(tabId, state) {
  const generation = generationsByTab.get(tabId);
  const previous = stateWritesByTab.get(tabId) || Promise.resolve();
  const next = previous.catch(() => {}).then(async () => {
    if (generation === generationsByTab.get(tabId)) {
      await chrome.storage.session.set({ [stateKey(tabId)]: state });
    }
  });
  stateWritesByTab.set(tabId, next);
  await next;
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
  generationsByTab.set(tabId, (generationsByTab.get(tabId) || 0) + 1);
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

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!sender.tab?.id) {
    return undefined;
  }

  const tabId = sender.tab.id;
  if (message.type === "verify-detector") {
    verifyDetectorVersion(message.detectorVersion).then(sendResponse, () => sendResponse({valid:false}));
    return true;
  }
  if (message.type === "detector-invalidated") {
    invalidateDetector(tabId, message);
    return undefined;
  }
  if (message.type === "video-cleared") {
    cancelTabRequest(tabId);
    chrome.storage.session.remove(transcriptKey(tabId));
    saveState(tabId, {
      status: message.videoId ? "loading" : "unsupported",
      videoId: message.videoId || null
    });
    return undefined;
  }
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
    if (!message.videoId || message.acquisitionMode === "unsupported") {
      notifyCurrentRequest(tabId, { status: "unsupported", videoId: message.videoId,
        requestId: message.requestId }, controller);
      clearCurrentRequest(tabId, controller);
    } else if (message.acquisitionMode === "conflict") {
      notifyCurrentRequest(tabId, {
        status: "unavailable", videoId: message.videoId, requestId: message.requestId,
        reason: "CONFLICTING_EXPERIMENT_SETTINGS"
      }, controller);
      clearCurrentRequest(tabId, controller);
    } else if (message.acquisitionMode === "disabled") {
      notifyCurrentRequest(tabId, { status: "disabled", videoId: message.videoId,
        requestId: message.requestId }, controller);
      clearCurrentRequest(tabId, controller);
    } else if (["preview", "experimental"].includes(message.acquisitionMode)) {
      acquirePreview(tabId, message, controller);
    } else if (message.acquisitionMode === "manual-fixture") {
      notifyCurrentRequest(tabId, {
        status: "manual-fixture", videoId: message.videoId, requestId: message.requestId
      }, controller);
      clearCurrentRequest(tabId, controller);
    } else if (message.acquisitionMode === "browser-probe") {
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

async function verifyDetectorVersion(expected) {
  const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  const origin = localBackendUrl(settings.backendUrl);
  if (!origin || !settings.enabled || !settings.experimentalAutoSkip) return {valid:false};
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch(new URL("/api/v1/demo-status", origin), {signal:controller.signal});
    const status = await response.json();
    return {valid:response.ok && status.detector_variant === "contextual_v1" &&
      status.detector_version === expected};
  } finally { clearTimeout(timeout); }
}

async function invalidateDetector(tabId, message) {
  const generation = generationsByTab.get(tabId);
  const stored = await chrome.storage.session.get(stateKey(tabId));
  const state = stored[stateKey(tabId)];
  if (generation !== generationsByTab.get(tabId) ||
      state?.videoId !== message.videoId || state?.requestId !== message.requestId) return;
  cancelTabRequest(tabId);
  const next = {...state,status:"unavailable",reason:"DETECTOR_REVALIDATION_FAILED",intervals:[]};
  await saveState(tabId, next);
  try { await chrome.tabs.sendMessage(tabId, {type:"acquisition-status",state:next}); }
  catch (_) { /* Navigation can remove the content script. */ }
}

async function acquirePreview(tabId, message, controller) {
  const { videoId, requestId } = message;
  const experimental = message.acquisitionMode === "experimental";
  let nativeBudget = null;
  const timeoutId = setTimeout(async () => {
    await notifyCurrentRequest(tabId, { status: "unavailable", videoId, requestId,
      reason: "DETECTION_TIMEOUT", nativeBudget }, controller);
    clearCurrentRequest(tabId, controller);
    controller.abort();
  }, 35000);
  requestMetadataByTab.get(tabId).timeoutId = timeoutId;
  try {
    const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
    if (!isCurrentRequest(tabId, controller)) return;
    if (
      !settings.enabled ||
      (experimental ? settings.experimentalAutoSkip !== true || settings.previewDetectedPromotions
        : settings.previewDetectedPromotions !== true || settings.experimentalAutoSkip) ||
      settings.developmentFixtures || settings.developmentBrowserAcquisition ||
      settings.previewTranscriptSource !== message.previewSource ||
      settings.sensitivity !== message.sensitivity
    ) {
      await notifyCurrentRequest(tabId, {
        status: "unavailable", videoId, requestId, reason: "PREVIEW_SETTINGS_CHANGED"
      }, controller);
      return;
    }
    const origin = localBackendUrl(settings.backendUrl);
    if (!origin || origin !== localBackendUrl(message.backendUrl)) {
      await notifyCurrentRequest(tabId, {
        status: "unavailable", videoId, requestId, reason: "LOCAL_BACKEND_REQUIRED"
      }, controller);
      return;
    }
    const source = settings.previewTranscriptSource;
    const mode = settings.sensitivity;
    if (experimental && (mode !== "conservative" || settings.detectorVariant !== "contextual_v1")) {
      await notifyCurrentRequest(tabId, {status: "unavailable", videoId, requestId,
        reason: "CONTEXTUAL_CONSERVATIVE_REQUIRED"}, controller);
      return;
    }
    if (!["saved", "supadata"].includes(source) ||
        !["conservative", "aggressive"].includes(mode)) {
      await notifyCurrentRequest(tabId, {
        status: "unavailable", videoId, requestId, reason: "INVALID_PREVIEW_SETTINGS"
      }, controller);
      return;
    }
    await notifyCurrentRequest(tabId, {
      status: "loading", videoId, requestId, mode, source
    }, controller);
    if (!isCurrentRequest(tabId, controller)) return;
    let expectedVersion = null;
    if (experimental) {
      const statusResponse = await fetch(new URL("/api/v1/demo-status", origin), {
        signal: controller.signal
      });
      const status = await statusResponse.json();
      nativeBudget = status;
      if (!isCurrentRequest(tabId, controller)) return;
      if (!statusResponse.ok || status.detector_variant !== "contextual_v1" ||
          !status.detector_version?.startsWith("contextual-v1-sha256:")) {
        await notifyCurrentRequest(tabId, {status: "unavailable", videoId, requestId, nativeBudget,
          reason: "CONTEXTUAL_BACKEND_REQUIRED"}, controller);
        return;
      }
      expectedVersion = status.detector_version;
    }
    const url = new URL(`/api/v1/detections/${videoId}`, origin);
    url.searchParams.set("mode", mode);
    url.searchParams.set("source", source);
    if (expectedVersion) url.searchParams.set("expected_detector_version", expectedVersion);
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { "X-Request-ID": requestId }
    });
    const body = await response.json();
    if (!isCurrentRequest(tabId, controller)) return;
    const latest = await chrome.storage.sync.get(DEFAULT_SETTINGS);
    if (!isCurrentRequest(tabId, controller) || !latest.enabled ||
        latest.experimentalAutoSkip !== settings.experimentalAutoSkip ||
        latest.previewDetectedPromotions !== settings.previewDetectedPromotions ||
        latest.previewTranscriptSource !== source || latest.sensitivity !== mode ||
        latest.detectorVariant !== settings.detectorVariant) return;
    if (!response.ok) {
      if (experimental) {
        const budgetResponse = await fetch(new URL("/api/v1/demo-status", origin), {
          signal: controller.signal
        });
        nativeBudget = await budgetResponse.json();
      }
      await notifyCurrentRequest(tabId, {
        status: "unavailable", videoId, requestId, mode, source, nativeBudget,
        reason: body?.error?.code || `HTTP_${response.status}`
      }, controller);
      return;
    }
    const state = validatePreviewResponse(body, { videoId, requestId, mode, source,
      experimental, detectorVersion: expectedVersion });
    await notifyCurrentRequest(tabId, state || {
      status: "unavailable", videoId, requestId, mode, source,
      reason: "INVALID_DETECTION_RESPONSE"
    }, controller);
    if (experimental && state && isCurrentRequest(tabId, controller)) {
      await chrome.tabs.sendMessage(tabId, {
        type: "promotion-intervals", videoId, requestId, mode,
        transcriptSource: source, detectorVersion: state.detectorVersion,
        source: "experimental-contextual-detector", intervals: state.intervals
      });
    }
  } catch (error) {
    if (error.name !== "AbortError") {
      await notifyCurrentRequest(tabId, {
        status: "unavailable", videoId, requestId, nativeBudget, reason: "BACKEND_UNREACHABLE"
      }, controller);
    }
  } finally {
    clearCurrentRequest(tabId, controller);
  }
}

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
