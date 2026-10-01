import { Router } from '@angular/router';

export const PENDING_QUESTION_KEY = 'trainu_pending_question';
/** Keep selected text out of the login URL and out of server-side query logs. */
export function stashExternalQuestion(router: Router, url: string): string {
  const tree = router.parseUrl(url);
  const draft = new URLSearchParams(tree.fragment ?? '').get('q') ?? tree.queryParams['q'];
  if (typeof draft === 'string' && draft.trim()) sessionStorage.setItem(PENDING_QUESTION_KEY, draft.trim().slice(0, 2000));
  delete tree.queryParams['q'];
  if (tree.fragment?.startsWith('q=')) tree.fragment = null;
  return router.serializeUrl(tree);
}
