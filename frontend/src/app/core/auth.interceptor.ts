import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, from, switchMap, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

/** Attaches the bearer token + active-org header to every API call, and on a
 * 401 (expired access token) tries exactly one silent refresh before
 * retrying the original request; if that fails the user is logged out.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const isApiCall = req.url.startsWith(environment.apiBaseUrl);
  const withAuthHeaders = (request: typeof req) => {
    if (!isApiCall) return request;
    const headers: Record<string, string> = {};
    if (auth.accessToken) headers['Authorization'] = `Bearer ${auth.accessToken}`;
    if (auth.activeOrgId()) headers['X-Org-Id'] = auth.activeOrgId()!;
    return request.clone({ setHeaders: headers });
  };

  return next(withAuthHeaders(req)).pipe(
    catchError((err: HttpErrorResponse) => {
      const isAuthEndpoint = req.url.includes('/auth/login') || req.url.includes('/auth/refresh');
      if (isApiCall && err.status === 401 && !isAuthEndpoint) {
        return from(auth.refreshAccessToken()).pipe(
          switchMap((ok) => {
            if (!ok) {
              auth.logout();
              router.navigate(['/login']);
              return throwError(() => err);
            }
            return next(withAuthHeaders(req));
          })
        );
      }
      return throwError(() => err);
    })
  );
};
