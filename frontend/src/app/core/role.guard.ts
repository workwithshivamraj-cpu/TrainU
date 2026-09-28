import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { Role } from './models';

/** Route-level guard mirroring the backend's role checks, so a lower-privileged
 * user can't reach an admin screen by typing the URL directly. The backend
 * still enforces every mutation independently — this guard only improves the
 * UX by not rendering a screen whose actions would just 403.
 */
export function roleGuard(minRole: Role): CanActivateFn {
  return () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    if (auth.hasAtLeastRole(minRole as any)) return true;
    router.navigate(['/dashboard']);
    return false;
  };
}
