import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { stashExternalQuestion } from './external-question';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = async (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isAuthenticated()) return true;
  const returnUrl = stashExternalQuestion(router, state.url);
  const signIn = () => router.createUrlTree(['/login'], { queryParams: { returnUrl } });
  if (!auth.accessToken && !auth.refreshToken) return signIn();
  try { await auth.loadCurrentUser(); return auth.isAuthenticated() || signIn(); }
  catch { return signIn(); }
};
