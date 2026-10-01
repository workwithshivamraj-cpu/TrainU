import { assistantUrl } from './url.js';
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => chrome.contextMenus.create({
    id: 'ask-trainu', title: 'Ask TrainU about this selection', contexts: ['selection'],
  }));
});
chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId !== 'ask-trainu') return;
  const { workspace } = await chrome.storage.local.get('workspace');
  try {
    if (!workspace) throw new Error('Workspace required');
    await chrome.tabs.create({ url: assistantUrl(workspace, info.selectionText) });
  } catch { await chrome.runtime.openOptionsPage(); }
});
