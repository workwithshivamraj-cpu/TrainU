import { workspaceOrigin } from './url.js';
const input = document.querySelector('#workspace');
const status = document.querySelector('#status');
const saved = await chrome.storage.local.get('workspace');
input.value = saved.workspace || '';
document.querySelector('form').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const workspace = workspaceOrigin(input.value);
    await chrome.storage.local.set({ workspace });
    input.value = workspace;
    status.textContent = 'Connected. Select text on a page, right-click, and choose Ask TrainU.';
    status.className = 'success';
  } catch (error) { status.textContent = error.message; status.className = 'error'; }
});
