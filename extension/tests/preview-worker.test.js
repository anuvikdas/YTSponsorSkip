const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const extensionRoot = path.resolve(__dirname, "..");

function harness() {
  const stored = new Map();
  const requests = [];
  const settings = {
    enabled: true, sensitivity: "conservative", previewDetectedPromotions: true,
    previewTranscriptSource: "saved", developmentFixtures: false,
    developmentBrowserAcquisition: false, backendUrl: "http://127.0.0.1:8000"
  };
  let onMessage;
  const sentToContent = [];
  const context = vm.createContext({
    URL, AbortController, Promise, Map, Date, setTimeout, clearTimeout,
    console,
    fetch: (url, options) => new Promise(resolve => {
      requests.push({ url: String(url), options, resolve });
    }),
    chrome: {
      runtime: { onMessage: { addListener(fn) { onMessage = fn; } } },
      storage: {
        sync: { get: async () => ({ ...settings }) },
        session: {
          async set(value) { for (const [key, item] of Object.entries(value)) stored.set(key, item); },
          async remove(key) { for (const item of Array.isArray(key) ? key : [key]) stored.delete(item); }
        }
      },
      tabs: {
        sendMessage: async (_tab, message) => sentToContent.push(message),
        onRemoved: { addListener() {} }
      }
    }
  });
  context.importScripts = (...names) => {
    for (const name of names) vm.runInContext(fs.readFileSync(path.join(extensionRoot, name), "utf8"), context);
  };
  vm.runInContext(fs.readFileSync(path.join(extensionRoot, "service-worker.js"), "utf8"), context);
  return {
    settings, requests, stored, sentToContent,
    send: (message) => onMessage(message, { tab: { id: 7 } }),
    flush: () => new Promise(resolve => setImmediate(resolve)),
    resolve: (request, identity, intervals = []) => request.resolve({
      ok: true, status: 200, json: async () => ({
        status: "ready", video_id: identity.videoId, request_id: identity.requestId,
        mode: identity.sensitivity, transcript_source: identity.previewSource,
        detector_version: "rules-test", transcript_provider: "saved-reviewed-tune",
        intervals
      })
    })
  };
}

test("late video-A response cannot replace video-B preview", async () => {
  const h = harness();
  const a = { type: "video-changed", acquisitionMode: "preview", videoId: "094y1Z2wpJg", requestId: "a", sensitivity: "conservative", previewSource: "saved", backendUrl: h.settings.backendUrl };
  const b = { ...a, videoId: "DTvS9lvRxZ8", requestId: "b" };
  h.send(a); await h.flush();
  assert.equal(h.requests.length, 1);
  h.send(b); await h.flush();
  assert.equal(h.requests.length, 2);
  h.resolve(h.requests[1], b, []); await h.flush();
  h.resolve(h.requests[0], a, [{ start_seconds: 10, end_seconds: 20 }]); await h.flush();
  assert.equal(h.stored.get("tab-7").videoId, b.videoId);
  assert.equal(h.stored.get("tab-7").status, "no-promotions");
  assert.equal(h.sentToContent.some(message => message.type === "promotion-intervals"), false);
});

test("mode/source switch and disable discard pending preview", async () => {
  const h = harness();
  const initial = { type: "video-changed", acquisitionMode: "preview", videoId: "094y1Z2wpJg", requestId: "one", sensitivity: "conservative", previewSource: "saved", backendUrl: h.settings.backendUrl };
  h.send(initial); await h.flush();
  h.settings.sensitivity = "aggressive";
  h.settings.previewTranscriptSource = "supadata";
  const changed = { ...initial, requestId: "two", sensitivity: "aggressive", previewSource: "supadata" };
  h.send(changed); await h.flush();
  h.resolve(h.requests[0], initial, [{ start_seconds: 1, end_seconds: 10 }]); await h.flush();
  assert.notEqual(h.stored.get("tab-7").requestId, "one");
  h.resolve(h.requests[1], changed, []); await h.flush();
  assert.equal(h.stored.get("tab-7").mode, "aggressive");
  assert.equal(h.stored.get("tab-7").source, "supadata");

  const pending = { ...changed, requestId: "three" };
  h.send(pending); await h.flush();
  h.send({ type: "video-cleared", videoId: null }); await h.flush();
  h.resolve(h.requests[2], pending, [{ start_seconds: 1, end_seconds: 10 }]); await h.flush();
  assert.equal(h.stored.get("tab-7").status, "unsupported");
});
