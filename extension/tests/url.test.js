import test from 'node:test';
import assert from 'node:assert/strict';
import { workspaceOrigin, assistantUrl } from '../url.js';
test('requires secure, credential-free workspace origins', () => {
  for (const value of ['javascript:alert(1)', 'data:text/html,a', 'http://example.com', 'https://user:pass@example.com', 'https://example.com/path', 'https://example.com?q=x', 'https://example.com#x', 'http://localhost.evil.com']) {
    assert.throws(() => workspaceOrigin(value));
  }
  assert.equal(workspaceOrigin('https://learn.example.com/'), 'https://learn.example.com');
  assert.equal(workspaceOrigin('http://localhost:4200'), 'http://localhost:4200');
});
test('selection remains in fragment and cannot change the destination', () => {
  const url = new URL(assistantUrl('https://learn.example.com', '</script>?token=secret&next=https://evil.com'));
  assert.equal(url.origin, 'https://learn.example.com');
  assert.equal(url.pathname, '/assistant');
  assert.equal(url.search, '');
  assert.equal(new URLSearchParams(url.hash.slice(1)).get('q'), '</script>?token=secret&next=https://evil.com');
});
test('selection is bounded and empty selection opens assistant', () => {
  const url = new URL(assistantUrl('https://learn.example.com', 'x'.repeat(5000)));
  assert.equal(new URLSearchParams(url.hash.slice(1)).get('q').length, 2000);
  assert.equal(assistantUrl('https://learn.example.com', '  '), 'https://learn.example.com/assistant');
});
