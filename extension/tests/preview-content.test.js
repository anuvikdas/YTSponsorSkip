const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

test("preview mode never hands intervals to playback or changes currentTime", async () => {
  const root = path.resolve(__dirname, "..");
  let runtimeListener;
  const documentListeners = new Map();
  const sent = [];
  const video = {
    currentTime: 12,
    addEventListener() {}, removeEventListener() {}
  };
  const settings = {
    enabled: true, sensitivity: "conservative", previewDetectedPromotions: true,
    previewTranscriptSource: "saved", developmentFixtures: false,
    developmentBrowserAcquisition: false, backendUrl: "http://127.0.0.1:8000",
    showNotifications: false
  };
  const location = { href: "https://www.youtube.com/watch?v=094y1Z2wpJg" };
  const context = vm.createContext({
    URL, Date, Promise, Set, Map, Number, Array, Object,
    location, crypto: { randomUUID: () => "test-uuid" },
    clearTimeout, setTimeout, setInterval: () => 0,
    MutationObserver: class { observe() {} },
    document: {
      documentElement: {}, body: { appendChild() {} },
      querySelector: selector => selector === "video" ? video : null,
      addEventListener: (name, callback) => documentListeners.set(name, callback),
      dispatchEvent() {}
    },
    window: { addEventListener() {} },
    chrome: {
      storage: {
        sync: { get: async () => ({ ...settings }) },
        onChanged: { addListener() {} }
      },
      runtime: {
        sendMessage: message => sent.push(message),
        onMessage: { addListener: callback => { runtimeListener = callback; } }
      }
    }
  });
  for (const name of ["defaults.js", "playback-controller.js", "development-fixtures.js", "content.js"]) {
    vm.runInContext(fs.readFileSync(path.join(root, name), "utf8"), context);
  }
  await new Promise(resolve => setImmediate(resolve));
  const current = sent.find(message => message.type === "video-changed");
  assert.equal(current.acquisitionMode, "preview");
  runtimeListener({
    type: "promotion-intervals", videoId: current.videoId, requestId: current.requestId,
    intervals: [{ startSeconds: 10, endSeconds: 20 }]
  });
  assert.equal(video.currentTime, 12);

  location.href = "https://www.youtube.com/watch?v=DTvS9lvRxZ8";
  documentListeners.get("yt-navigate-finish")();
  await new Promise(resolve => setImmediate(resolve));
  runtimeListener({
    type: "promotion-intervals", videoId: current.videoId, requestId: current.requestId,
    intervals: [{ startSeconds: 0, endSeconds: 100 }]
  });
  assert.equal(video.currentTime, 12);
  assert.equal(sent.filter(message => message.type === "video-changed").length, 2);
});
