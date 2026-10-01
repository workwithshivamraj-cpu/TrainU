import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, from, switchMap, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const isApiCall = req.url === environment.apiBaseUrl || req.url.startsWith(environment.apiBaseUrl + '/');
  const isAuthEndpoint = /\/auth\/(login|refresh|register|logout)(\?|$)/.test(req.url);
  const originalToken = auth.accessToken;
  const withAuthHeaders = (request: typeof req) => {
    if (!isApiCall) return request;
    const headers: Record<string, string> = {};
    if (auth.accessToken) headers['Authorization'] = `Bearer ${auth.accessToken}`;
    if (auth.activeOrgId()) headers['X-Org-Id'] = auth.activeOrgId()!;
    return request.clone({ setHeaders: headers });
  };
  return next(withAuthHeaders(req)).pipe(catchError((err: HttpErrorResponse) => {
    if (!isApiCall || err.status !== 401 || isAuthEndpoint) return throwError(() => err);
    // A parallel request may already have refreshed the token.
    const refreshed = auth.accessToken && auth.accessToken !== originalToken
      ? Promise.resolve(true) : auth.refreshAccessToken();
    return from(refreshed).pipe(switchMap(ok => {
      if (!ok) { auth.logout(false); return throwError(() => err); }
      return next(withAuthHeaders(req)).pipe(catchError(retryError => {
        if (retryError.status === 401) auth.logout(false);
        return throwError(() => retryError);
      }));
    }));
  }));
};
