# Chrome playback test checklist

These checks use manual `tune` fixtures, not detector results. The backend may still report `IP_BLOCKED`; that does not prevent fixture-based playback testing.

## Start and reload

1. From the repository root, run:

   ```bash
   .venv/bin/uvicorn ytsponsorskip.main:app --host 127.0.0.1 --port 8000
   ```

2. Open `chrome://extensions`. Enable **Developer mode**.
3. If YTSponsorSkip is not loaded, choose **Load unpacked** and select `/Users/anuvikdas/Downloads/YTSponsorSkip/YTSponsorSkip/extension`. Otherwise click the extension card's reload button.
4. Open **Details → Extension options → Development**. Select **Use manual playback fixtures**, keep notifications enabled, and save.

## Skip and Undo

1. Open `https://www.youtube.com/watch?v=-lErGZZgUbY`.
2. Wait two seconds for the fixture, seek to 50 seconds, and play.
3. Expected at 53 seconds: playback jumps to 74 seconds and a notification says it skipped a manual development fixture.
4. Click **Undo** within six seconds. Expected: playback returns to the actual pre-skip position near 53 seconds and does not immediately skip again.
5. Let playback pass 74 seconds, then seek back to 50 seconds and play. Expected: the interval is eligible again and skips at 53 seconds.

## Explicit seeking

1. Seek directly to 60 seconds. Expected: the controller treats this as an explicit user choice and allows playback through the interval.
2. Seek to 50 seconds and play normally. Expected: playback skips when it reaches 53 seconds.
3. Seek to 80 seconds. Expected: no rewind and no skip.

## Negative and navigation checks

1. Open `https://www.youtube.com/watch?v=U3aXWizDbQ4`. Expected: this reviewed tune negative has an empty fixture and never auto-skips.
2. Open `-lErGZZgUbY`, then navigate to `MRtg6A1f2Ko` within 1.5 seconds. Expected: the old delayed fixture is discarded. The second video's interval is 35–104 seconds.
3. Seek the second video to 30 seconds and play. Expected: only the second video's interval is used.

## Late arrival and paused behavior

The automated suite verifies interval arrival while already inside a playing or paused interval, including preserving the paused state and never rewinding after an interval. The 1.5-second Chrome fixture delay lets you observe late arrival during natural playback, but manually seeking inside an interval intentionally suppresses that interval under the approved user-seeking policy.

After testing, turn **Use manual playback fixtures** off so labels cannot be mistaken for detector output.
