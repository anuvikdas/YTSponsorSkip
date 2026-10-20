const form = document.querySelector("#settings-form");
const enabled = document.querySelector("#enabled");
const showNotifications = document.querySelector("#show-notifications");
const developmentFixtures = document.querySelector("#development-fixtures");
const developmentBrowserAcquisition = document.querySelector(
  "#development-browser-acquisition"
);
const previewDetectedPromotions = document.querySelector("#preview-detected-promotions");
const previewTranscriptSource = document.querySelector("#preview-transcript-source");
const backendUrl = document.querySelector("#backend-url");
const status = document.querySelector("#status");

async function restoreSettings() {
  const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  enabled.checked = settings.enabled;
  showNotifications.checked = settings.showNotifications;
  developmentFixtures.checked = settings.developmentFixtures;
  developmentBrowserAcquisition.checked = settings.developmentBrowserAcquisition;
  previewDetectedPromotions.checked = settings.previewDetectedPromotions;
  previewTranscriptSource.value = settings.previewTranscriptSource;
  backendUrl.value = settings.backendUrl;
  const sensitivity = document.querySelector(
    `input[name="sensitivity"][value="${settings.sensitivity}"]`
  );
  (sensitivity || document.querySelector('[value="conservative"]')).checked = true;
}

function normalizedBackendUrl() {
  return backendUrl.value.trim().replace(/\/$/, "");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const sensitivity = document.querySelector('input[name="sensitivity"]:checked').value;
  const localUrl = localBackendUrl(normalizedBackendUrl());
  if (previewDetectedPromotions.checked && !localUrl) {
    status.textContent = "Preview requires the local backend on port 8000.";
    return;
  }
  if (previewDetectedPromotions.checked &&
      (developmentFixtures.checked || developmentBrowserAcquisition.checked)) {
    status.textContent = "Turn off manual fixtures and the browser probe before preview.";
    return;
  }
  await chrome.storage.sync.set({
    enabled: enabled.checked,
    sensitivity,
    showNotifications: showNotifications.checked,
    developmentFixtures: developmentFixtures.checked,
    developmentBrowserAcquisition: developmentBrowserAcquisition.checked,
    previewDetectedPromotions: previewDetectedPromotions.checked,
    previewTranscriptSource: previewTranscriptSource.value,
    backendUrl: normalizedBackendUrl()
  });
  status.textContent = "Settings saved.";
  setTimeout(() => { status.textContent = ""; }, 1500);
});

document.querySelector("#reset").addEventListener("click", async () => {
  await chrome.storage.sync.set(DEFAULT_SETTINGS);
  await restoreSettings();
  status.textContent = "Defaults restored.";
});

previewDetectedPromotions.addEventListener("change", () => {
  if (previewDetectedPromotions.checked) {
    developmentFixtures.checked = false;
    developmentBrowserAcquisition.checked = false;
  }
});
for (const exclusive of [developmentFixtures, developmentBrowserAcquisition]) {
  exclusive.addEventListener("change", () => {
    if (exclusive.checked) previewDetectedPromotions.checked = false;
  });
}

restoreSettings();
