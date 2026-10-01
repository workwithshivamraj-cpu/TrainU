import { assistantUrl, workspaceOrigin } from './url.js';
const { workspace } = await chrome.storage.local.get('workspace');
if (workspace) document.querySelector('#workspace').textContent = workspace;
async function open(path) {
  try {
    if (!workspace) return chrome.runtime.openOptionsPage();
    const url = path === 'ask' ? assistantUrl(workspace) : new URL('/sources/upload', workspaceOrigin(workspace)).href;
    await chrome.tabs.create({ url });
    window.close();
  } catch (error) { document.querySelector('#error').textContent = error.message; }
}
document.querySelector('#ask').addEventListener('click', () => open('ask'));
document.querySelector('#upload').addEventListener('click', () => open('upload'));
document.querySelector('#settings').addEventListener('click', () => chrome.runtime.openOptionsPage());
