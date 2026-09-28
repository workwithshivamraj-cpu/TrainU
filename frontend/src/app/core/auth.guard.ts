import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) return true;
  if (!auth.accessToken) {
    router.navigate(['/login']);
    return false;
  }
  try {
    await auth.loadCurrentUser();
    return true;
  } catch {
    router.navigate(['/login']);
    return false;
  }
};
