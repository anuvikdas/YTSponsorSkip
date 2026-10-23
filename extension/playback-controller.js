// The playback safety policy is applied after adjacent/overlapping intervals merge.
const MINIMUM_AUTO_SKIP_DURATION_SECONDS = 3;

class PlaybackController {
  constructor({ onSkip = () => {}, onUndo = () => {}, seekToleranceSeconds = 0.35,
    canSeek = () => true } = {}) {
    this.onSkip = onSkip;
    this.onUndo = onUndo;
    this.seekToleranceSeconds = seekToleranceSeconds;
    this.canSeek = canSeek;
    this.video = null;
    this.videoId = null;
    this.requestId = null;
    this.intervals = [];
    this.suppressedIntervalIds = new Set();
    this.internalSeek = null;
    this.userSeeking = false;
    this.lastUserSeekLandingTime = null;
    this.undoRecord = null;

    this.handleTimeUpdate = this.handleTimeUpdate.bind(this);
    this.handleSeeking = this.handleSeeking.bind(this);
    this.handleSeeked = this.handleSeeked.bind(this);
  }

  attachVideo(video) {
    if (video === this.video) return;
    this.detachVideo();
    this.video = video || null;
    if (!this.video) return;
    this.video.addEventListener("timeupdate", this.handleTimeUpdate);
    this.video.addEventListener("playing", this.handleTimeUpdate);
    this.video.addEventListener("loadedmetadata", this.handleTimeUpdate);
    this.video.addEventListener("durationchange", this.handleTimeUpdate);
    this.video.addEventListener("seeking", this.handleSeeking);
    this.video.addEventListener("seeked", this.handleSeeked);
    this.evaluatePlayback("video-attached");
  }

  detachVideo() {
    if (!this.video) return;
    this.video.removeEventListener("timeupdate", this.handleTimeUpdate);
    this.video.removeEventListener("playing", this.handleTimeUpdate);
    this.video.removeEventListener("loadedmetadata", this.handleTimeUpdate);
    this.video.removeEventListener("durationchange", this.handleTimeUpdate);
    this.video.removeEventListener("seeking", this.handleSeeking);
    this.video.removeEventListener("seeked", this.handleSeeked);
    this.video = null;
  }

  beginVideo(videoId, requestId) {
    this.videoId = videoId;
    this.requestId = requestId;
    this.intervals = [];
    this.suppressedIntervalIds.clear();
    this.internalSeek = null;
    this.userSeeking = false;
    this.lastUserSeekLandingTime = null;
    this.undoRecord = null;
  }

  setIntervals({ videoId, requestId, intervals, source = "detector" }) {
    if (videoId !== this.videoId || requestId !== this.requestId) return false;
    this.intervals = this.normalizeIntervals(intervals, source);
    this.suppressedIntervalIds.clear();
    this.undoRecord = null;
    const currentTime = Number(this.video?.currentTime);
    if (Number.isFinite(currentTime) && Number.isFinite(this.lastUserSeekLandingTime)) {
      for (const interval of this.intervals) {
        if (
          this.contains(interval, this.lastUserSeekLandingTime) &&
          this.contains(interval, currentTime)
        ) {
          this.suppressedIntervalIds.add(interval.id);
        }
      }
    }
    this.evaluatePlayback("intervals-arrived");
    return true;
  }

  normalizeIntervals(intervals, source) {
    // Fail closed on malformed or unordered input, rather than coercing strings into times.
    if (!Array.isArray(intervals) || intervals.some((item, index) =>
      !item || typeof item.startSeconds !== "number" || !Number.isFinite(item.startSeconds) ||
      typeof item.endSeconds !== "number" || !Number.isFinite(item.endSeconds) ||
      item.startSeconds < 0 || item.endSeconds <= item.startSeconds ||
      (index > 0 && item.startSeconds < intervals[index - 1].startSeconds))) return [];
    const sorted = (Array.isArray(intervals) ? intervals : [])
      .map((interval) => ({
        startSeconds: Number(interval.startSeconds),
        endSeconds: Number(interval.endSeconds)
      }))
      .filter(
        (interval) =>
          Number.isFinite(interval.startSeconds) &&
          Number.isFinite(interval.endSeconds) &&
          interval.startSeconds >= 0 &&
          interval.endSeconds > interval.startSeconds
      )
      .sort((left, right) => left.startSeconds - right.startSeconds);

    const merged = [];
    for (const interval of sorted) {
      const previous = merged.at(-1);
      if (previous && interval.startSeconds <= previous.endSeconds) {
        previous.endSeconds = Math.max(previous.endSeconds, interval.endSeconds);
        previous.memberCount += 1;
      } else {
        merged.push({ ...interval, source, memberCount: 1 });
      }
    }
    return merged
      .filter((interval) => interval.endSeconds - interval.startSeconds > MINIMUM_AUTO_SKIP_DURATION_SECONDS)
      .map((interval, index) => ({
      ...interval,
      id: `${this.videoId}:${this.requestId}:${index}:${interval.startSeconds}:${interval.endSeconds}`
      }));
  }

  handleSeeking() {
    if (!this.video) return;
    const currentTime = Number(this.video.currentTime);
    if (
      this.internalSeek &&
      Math.abs(currentTime - this.internalSeek.targetSeconds) <= this.seekToleranceSeconds
    ) {
      this.internalSeek.observed = true;
      return;
    }
    this.internalSeek = null;
    this.userSeeking = true;
  }

  handleSeeked() {
    if (!this.video) return;
    const currentTime = Number(this.video.currentTime);
    if (
      this.internalSeek &&
      Math.abs(currentTime - this.internalSeek.targetSeconds) <= this.seekToleranceSeconds
    ) {
      this.internalSeek = null;
      this.userSeeking = false;
      this.releaseSuppression(currentTime);
      return;
    }

    this.internalSeek = null;
    this.userSeeking = false;
    this.lastUserSeekLandingTime = currentTime;
    this.releaseSuppression(currentTime);
    for (const interval of this.intervals) {
      if (this.contains(interval, currentTime)) {
        this.suppressedIntervalIds.add(interval.id);
      }
    }
  }

  handleTimeUpdate() {
    if (!this.video || this.video.seeking || this.userSeeking) return;
    this.releaseSuppression(Number(this.video.currentTime));
    this.evaluatePlayback("playback");
  }

  evaluatePlayback(reason) {
    if (!this.video || this.video.seeking || this.userSeeking || this.internalSeek ||
        !this.canSeek()) return false;
    const duration = this.video.duration;
    if (!Number.isFinite(duration) || duration <= 0) return false;
    const currentTime = Number(this.video.currentTime);
    if (!Number.isFinite(currentTime) || currentTime < 0 || currentTime > duration) return false;
    this.releaseSuppression(currentTime);
    const interval = this.intervals.find((candidate) => this.contains(candidate, currentTime));
    if (!interval || interval.endSeconds > duration || this.suppressedIntervalIds.has(interval.id)) return false;
    if (interval.endSeconds <= currentTime) return false;
    return this.skipInterval(interval, currentTime, reason);
  }

  skipInterval(interval, preSkipTime, reason) {
    if (!this.video) return false;
    this.undoRecord = {
      videoId: this.videoId,
      requestId: this.requestId,
      intervalId: interval.id,
      preSkipTime,
      destination: interval.endSeconds
    };
    this.internalSeek = {
      targetSeconds: interval.endSeconds,
      observed: false,
      reason: "automatic-skip"
    };
    try { this.video.currentTime = interval.endSeconds; }
    catch (_) { this.internalSeek = null; this.undoRecord = null; return false; }
    this.onSkip({
      videoId: this.videoId,
      requestId: this.requestId,
      source: interval.source,
      memberCount: interval.memberCount,
      startSeconds: interval.startSeconds,
      endSeconds: interval.endSeconds,
      preSkipTime,
      reason
    });
    return true;
  }

  undoLastSkip() {
    if (!this.video || !this.undoRecord) return false;
    const record = this.undoRecord;
    if (record.videoId !== this.videoId || record.requestId !== this.requestId) return false;
    if (!this.canSeek() || !Number.isFinite(this.video.duration) ||
        record.preSkipTime < 0 || record.preSkipTime > this.video.duration) return false;
    this.suppressedIntervalIds.add(record.intervalId);
    this.internalSeek = {
      targetSeconds: record.preSkipTime,
      observed: false,
      reason: "undo"
    };
    this.undoRecord = null;
    try { this.video.currentTime = record.preSkipTime; }
    catch (_) { this.internalSeek = null; return false; }
    this.onUndo({
      videoId: this.videoId,
      requestId: this.requestId,
      restoredTime: record.preSkipTime
    });
    return true;
  }

  releaseSuppression(currentTime) {
    for (const interval of this.intervals) {
      if (
        this.suppressedIntervalIds.has(interval.id) &&
        !this.contains(interval, currentTime)
      ) {
        this.suppressedIntervalIds.delete(interval.id);
      }
    }
    if (
      Number.isFinite(this.lastUserSeekLandingTime) &&
      this.intervals.length > 0 &&
      !this.intervals.some(
        (interval) =>
          this.contains(interval, this.lastUserSeekLandingTime) &&
          this.contains(interval, currentTime)
      )
    ) {
      this.lastUserSeekLandingTime = null;
    }
  }

  contains(interval, currentTime) {
    return currentTime >= interval.startSeconds && currentTime < interval.endSeconds;
  }

  snapshot() {
    return {
      videoId: this.videoId,
      requestId: this.requestId,
      intervalCount: this.intervals.length,
      suppressedCount: this.suppressedIntervalIds.size,
      hasUndo: Boolean(this.undoRecord),
      internalSeekReason: this.internalSeek?.reason || null
    };
  }

  destroy() {
    this.detachVideo();
    this.beginVideo(null, null);
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { PlaybackController };
} else {
  globalThis.PlaybackController = PlaybackController;
}
