const test = require("node:test");
const assert = require("node:assert/strict");

const { PlaybackController } = require("../playback-controller.js");
const { DEVELOPMENT_PLAYBACK_FIXTURES } = require("../development-fixtures.js");

class FakeVideo {
  constructor(currentTime = 0, paused = false) {
    this._currentTime = currentTime;
    this.paused = paused;
    this.seeking = false;
    this.listeners = new Map();
  }

  get currentTime() {
    return this._currentTime;
  }

  set currentTime(value) {
    this._currentTime = value;
    this.seeking = true;
    this.emit("seeking");
    this.seeking = false;
    this.emit("seeked");
  }

  addEventListener(type, listener) {
    const listeners = this.listeners.get(type) || new Set();
    listeners.add(listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(type, listener) {
    this.listeners.get(type)?.delete(listener);
  }

  emit(type) {
    for (const listener of this.listeners.get(type) || []) listener();
  }

  tick(time) {
    this._currentTime = time;
    this.emit("timeupdate");
  }

  userSeek(time) {
    this._currentTime = time;
    this.seeking = true;
    this.emit("seeking");
    this.seeking = false;
    this.emit("seeked");
  }
}

function setup({ currentTime = 0, paused = false } = {}) {
  const skips = [];
  const undos = [];
  const video = new FakeVideo(currentTime, paused);
  const controller = new PlaybackController({
    onSkip: (event) => skips.push(event),
    onUndo: (event) => undos.push(event)
  });
  controller.attachVideo(video);
  controller.beginVideo("video-a", "request-a");
  return { controller, video, skips, undos };
}

function setInterval(controller, startSeconds = 10, endSeconds = 20) {
  return controller.setIntervals({
    videoId: "video-a",
    requestId: "request-a",
    source: "manual-tune-fixture",
    intervals: [{ startSeconds, endSeconds }]
  });
}

test("normal playback skips at the interval start", () => {
  const { controller, video, skips } = setup();
  setInterval(controller);
  video.tick(9.9);
  assert.equal(video.currentTime, 9.9);
  video.tick(10);
  assert.equal(video.currentTime, 20);
  assert.equal(skips.length, 1);
});

test("late intervals skip remaining time while paused without changing pause state", () => {
  const { controller, video, skips } = setup({ currentTime: 15, paused: true });
  setInterval(controller);
  assert.equal(video.currentTime, 20);
  assert.equal(video.paused, true);
  assert.equal(skips[0].preSkipTime, 15);
});

test("late intervals never rewind playback that is already past them", () => {
  const { controller, video, skips } = setup({ currentTime: 25 });
  setInterval(controller);
  assert.equal(video.currentTime, 25);
  assert.equal(skips.length, 0);
});

test("a user seek into an interval wins even when intervals arrive later", () => {
  const { controller, video, skips } = setup();
  video.userSeek(12);
  video.tick(13);
  setInterval(controller);
  assert.equal(video.currentTime, 13);
  assert.equal(skips.length, 0);

  video.tick(20);
  video.userSeek(5);
  video.tick(10);
  assert.equal(video.currentTime, 20);
  assert.equal(skips.length, 1);
});

test("user seeking before, into, and after intervals follows explicit-seek policy", () => {
  const { controller, video, skips } = setup();
  setInterval(controller);

  video.userSeek(5);
  video.tick(10);
  assert.equal(video.currentTime, 20);
  assert.equal(skips.length, 1);

  video.userSeek(12);
  video.tick(13);
  assert.equal(video.currentTime, 13);
  assert.equal(skips.length, 1);

  video.tick(20);
  video.userSeek(25);
  assert.equal(video.currentTime, 25);
  assert.equal(skips.length, 1);
});

test("undo restores the exact pre-skip time without an immediate re-skip", () => {
  const { controller, video, skips, undos } = setup();
  setInterval(controller);
  video.tick(12.5);
  assert.equal(video.currentTime, 20);

  assert.equal(controller.undoLastSkip(), true);
  assert.equal(video.currentTime, 12.5);
  video.tick(13);
  assert.equal(video.currentTime, 13);
  assert.equal(skips.length, 1);
  assert.equal(undos.length, 1);
});

test("leaving a suppressed interval makes it eligible on replay", () => {
  const { controller, video, skips } = setup();
  setInterval(controller);
  video.userSeek(12);
  video.tick(15);
  assert.equal(skips.length, 0);
  video.tick(20);
  video.userSeek(5);
  video.tick(10);
  assert.equal(video.currentTime, 20);
  assert.equal(skips.length, 1);
});

test("adjacent intervals produce one seek to the end of the group", () => {
  const { controller, video, skips } = setup();
  controller.setIntervals({
    videoId: "video-a",
    requestId: "request-a",
    intervals: [
      { startSeconds: 10, endSeconds: 15 },
      { startSeconds: 15, endSeconds: 22 }
    ]
  });
  video.tick(10);
  assert.equal(video.currentTime, 22);
  assert.equal(skips.length, 1);
  assert.equal(skips[0].memberCount, 2);
});

test("navigation clears state and rejects stale interval results", () => {
  const { controller, video, skips } = setup();
  setInterval(controller);
  controller.beginVideo("video-b", "request-b");
  const accepted = controller.setIntervals({
    videoId: "video-a",
    requestId: "request-a",
    intervals: [{ startSeconds: 0, endSeconds: 100 }]
  });
  video.tick(10);
  assert.equal(accepted, false);
  assert.equal(video.currentTime, 10);
  assert.equal(skips.length, 0);
  assert.deepEqual(controller.snapshot(), {
    videoId: "video-b",
    requestId: "request-b",
    intervalCount: 0,
    suppressedCount: 0,
    hasUndo: false,
    internalSeekReason: null
  });
});

test("development fixtures contain only fully reviewed tune videos", () => {
  const expectedTuneVideoIds = [
    "094y1Z2wpJg",
    "bHIhgxav9LY",
    "iWeu2dxHRDg",
    "DTvS9lvRxZ8",
    "I9hJ_Rux9y0",
    "lXfEK8G8CUI",
    "-lErGZZgUbY",
    "MRtg6A1f2Ko",
    "9lx11dy9J30",
    "Sew4rctKghY",
    "O7sQBfpQCvU",
    "U3aXWizDbQ4",
    "x7X9w_GIm1s",
    "aircAruvnKk"
  ].sort();
  assert.deepEqual(Object.keys(DEVELOPMENT_PLAYBACK_FIXTURES).sort(), expectedTuneVideoIds);
  assert.equal(DEVELOPMENT_PLAYBACK_FIXTURES["0_KhihMIOG8"], undefined);
  assert.equal(DEVELOPMENT_PLAYBACK_FIXTURES["jHP942Livy0"], undefined);
});
