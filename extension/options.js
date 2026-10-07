const form = document.querySelector("#settings-form");
const enabled = document.querySelector("#enabled");
const showNotifications = document.querySelector("#show-notifications");
const backendUrl = document.querySelector("#backend-url");
const status = document.querySelector("#status");

async function restoreSettings() {
  const settings = await chrome.storage.sync.get(DEFAULT_SETTINGS);
  enabled.checked = settings.enabled;
  showNotifications.checked = settings.showNotifications;
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
  await chrome.storage.sync.set({
    enabled: enabled.checked,
    sensitivity,
    showNotifications: showNotifications.checked,
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

restoreSettings();
