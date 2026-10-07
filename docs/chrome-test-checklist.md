# Chrome extension test checklist

These are manual checks until Chrome browser control is connected. Record the date, Chrome version, extension commit, and observed result; do not mark a check automated.

## Load the unpacked extension

1. Start the backend from the repository root:

   ```bash
   .venv/bin/uvicorn ytsponsorskip.main:app --host 127.0.0.1 --port 8000
   ```

2. Open `chrome://extensions`, turn on **Developer mode**, and choose **Load unpacked**.
3. Select the absolute directory `/Users/anuvikdas/Downloads/YTSponsorSkip/YTSponsorSkip/extension`.
4. Open the extension's **Details → Extension options**. Confirm **Enabled** and **Show unavailable notifications** are selected, **Conservative** is selected, and the backend URL is `http://127.0.0.1:8000`. Save.

## Acquisition and playback

1. Open `https://www.youtube.com/watch?v=dQw4w9WgXcQ` and press Play immediately.
2. Expected: playback starts without waiting for the backend. The popup first says it is retrieving a transcript.
3. If acquisition succeeds, expected: the popup reports the manual/generated type and snippet count. If the current IP is still blocked, expected: a six-second unavailable notice appears, the popup shows `IP_BLOCKED`, and playback continues without seeking or pausing.
4. Open `https://www.youtube.com/watch?v=aaaaaaaaaaa`. Expected: the extension reports `VIDEO_UNAVAILABLE`; no playback-control action is attempted.

## Pending-request navigation race

1. In a YouTube tab, open video A: `https://www.youtube.com/watch?v=rfscVS0vtbw`.
2. Immediately, before the popup settles, paste video B into the same tab: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`.
3. Wait for the current request to finish and open the popup. Expected: its state belongs only to video B; a result for video A must not replace it.
4. For an exact identity check, open `chrome://extensions`, find YTSponsorSkip, choose the **service worker** inspection link, and run `chrome.storage.session.get(null, console.log)` in its console. Find the current tab's `tab-<number>` entry. Expected: `videoId` is `dQw4w9WgXcQ`; its `requestId` begins with that same ID.
5. Expected on the page: no stale video-A unavailable notice appears after video B is current. Video B may show its own unavailable notice if acquisition fails.

## Settings smoke check

1. Change sensitivity to **Aggressive**, save, close, and reopen options. Expected: Aggressive remains selected.
2. Choose **Restore defaults**. Expected: Conservative is selected again.
3. Disable the extension in options and navigate to another video. Expected: the popup says skipping is disabled and no acquisition request is made.

Sensitivity is stored now but does not alter behavior until a detector exists. These checks validate acquisition state and navigation safety, not skipping.
