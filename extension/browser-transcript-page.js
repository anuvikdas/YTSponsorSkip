(function () {
  "use strict";

  const CHANNEL = "ytss-browser-transcript-v1";
  const REQUEST_EVENT = "ytss-browser-transcript-request";
  const PAGE_DATA_TIMEOUT_MS = 5000;
  const POLL_INTERVAL_MS = 100;

  function isRequest(value) {
    return (
      value &&
      typeof value === "object" &&
      Object.keys(value).every((key) => ["videoId", "requestId"].includes(key)) &&
      typeof value.videoId === "string" &&
      /^[A-Za-z0-9_-]{11}$/.test(value.videoId) &&
      typeof value.requestId === "string" &&
      value.requestId.length >= 12 &&
      value.requestId.length <= 160
    );
  }

  function postResult(videoId, requestId, value) {
    window.postMessage(
      {
        channel: CHANNEL,
        type: "result",
        videoId,
        requestId,
        ...value
      },
      location.origin
    );
  }

  function playerResponseFor(videoId) {
    const player = document.querySelector("#movie_player");
    const candidates = [
      typeof player?.getPlayerResponse === "function" ? player.getPlayerResponse() : null,
      window.ytInitialPlayerResponse
    ];
    return candidates.find((candidate) => candidate?.videoDetails?.videoId === videoId) || null;
  }

  async function waitForCaptionTracks(videoId) {
    const deadline = performance.now() + PAGE_DATA_TIMEOUT_MS;
    while (performance.now() < deadline) {
      const response = playerResponseFor(videoId);
      if (response) {
        const tracks = response.captions?.playerCaptionsTracklistRenderer?.captionTracks;
        if (Array.isArray(tracks)) return tracks;
        if (response.playabilityStatus?.status && response.playabilityStatus.status !== "OK") {
          return [];
        }
      }
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    }
    return null;
  }

  function trackName(track) {
    if (typeof track.name?.simpleText === "string") return track.name.simpleText;
    if (Array.isArray(track.name?.runs)) {
      return track.name.runs.map((run) => run.text || "").join("");
    }
    return track.languageCode || "English";
  }

  function chooseEnglishTrack(tracks) {
    const english = tracks.filter((track) => {
      const code = String(track.languageCode || "").toLowerCase();
      return code === "en" || code.startsWith("en-");
    });
    return (
      english.find((track) => track.kind !== "asr" && !String(track.vssId).startsWith("a.")) ||
      english[0] ||
      null
    );
  }

  function fixedTimedTextUrl(baseUrl) {
    const url = new URL(baseUrl, location.origin);
    if (
      url.protocol !== "https:" ||
      url.hostname !== location.hostname ||
      url.pathname !== "/api/timedtext"
    ) {
      throw new Error("UNSAFE_TIMED_TEXT_URL");
    }
    url.searchParams.set("fmt", "json3");
    return url.toString();
  }

  function parseJson3(document) {
    if (!Array.isArray(document?.events)) throw new Error("INVALID_JSON3");
    const snippets = [];
    for (const event of document.events) {
      if (!Array.isArray(event.segs) || !Number.isFinite(event.tStartMs)) continue;
      const text = event.segs.map((segment) => segment.utf8 || "").join("");
      if (!text.trim()) continue;
      snippets.push({
        index: snippets.length,
        text,
        startSeconds: event.tStartMs / 1000,
        durationSeconds: Number.isFinite(event.dDurationMs) ? event.dDurationMs / 1000 : 0
      });
    }
    if (!snippets.length) throw new Error("EMPTY_JSON3");
    return snippets;
  }

  async function acquire(videoId, requestId) {
    const started = performance.now();
    const tracks = await waitForCaptionTracks(videoId);
    const metadataDiscoveryMs = performance.now() - started;
    if (tracks === null) {
      postResult(videoId, requestId, {
        ok: false,
        error: { code: "PAGE_DATA_UNAVAILABLE" }
      });
      return;
    }
    const track = chooseEnglishTrack(tracks);
    if (!track?.baseUrl) {
      postResult(videoId, requestId, {
        ok: false,
        error: { code: "NO_CAPTION_TRACK" }
      });
      return;
    }

    let response;
    const fetchStarted = performance.now();
    try {
      response = await fetch(fixedTimedTextUrl(track.baseUrl), {
        method: "GET",
        credentials: "include",
        redirect: "error"
      });
    } catch (_) {
      postResult(videoId, requestId, {
        ok: false,
        error: { code: "TIMED_TEXT_HTTP_ERROR" }
      });
      return;
    }
    if (!response.ok) {
      postResult(videoId, requestId, {
        ok: false,
        error: { code: "TIMED_TEXT_HTTP_ERROR" }
      });
      return;
    }

    try {
      const snippets = parseJson3(await response.json());
      const completed = performance.now();
      postResult(videoId, requestId, {
        ok: true,
        payload: {
          language: trackName(track),
          languageCode: track.languageCode,
          isGenerated: track.kind === "asr" || String(track.vssId).startsWith("a."),
          providerLatencyMs: completed - started,
          metadataDiscoveryMs,
          timedTextFetchMs: completed - fetchStarted,
          snippets
        }
      });
    } catch (_) {
      postResult(videoId, requestId, {
        ok: false,
        error: { code: "TIMED_TEXT_PARSE_ERROR" }
      });
    }
  }

  document.addEventListener(REQUEST_EVENT, (event) => {
    if (!isRequest(event.detail)) return;
    void acquire(event.detail.videoId, event.detail.requestId);
  });
})();
