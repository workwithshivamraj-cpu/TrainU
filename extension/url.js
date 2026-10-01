export function workspaceOrigin(value) {
  let url;
  try { url = new URL(String(value).trim()); } catch { throw new Error('Enter a valid workspace URL, such as https://learn.yourcompany.com.'); }
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if (url.protocol !== 'https:' && !(local && url.protocol === 'http:')) {
    throw new Error('Use HTTPS. HTTP is allowed only for local development.');
  }
  if (url.username || url.password || url.search || url.hash || url.pathname !== '/') {
    throw new Error('Enter only the workspace origin, without a path, credentials, query, or fragment.');
  }
  return url.origin;
}
export function assistantUrl(origin, selection = '') {
  const url = new URL('/assistant', workspaceOrigin(origin));
  const prompt = String(selection).trim().slice(0, 2000);
  if (prompt) url.hash = new URLSearchParams({ q: prompt }).toString();
  return url.href;
}
