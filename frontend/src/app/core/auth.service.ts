import { HttpClient } from '@angular/common/http';
import { Injectable, computed, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';
import { Membership, User } from './models';

interface TokenResponse { access_token: string; refresh_token: string; token_type: string; }
const ACCESS_KEY = 'trainu_access_token';
const REFRESH_KEY = 'trainu_refresh_token';
const ORG_KEY = 'trainu_active_org';

@Injectable({ providedIn: 'root' })
export class AuthService {
  readonly user = signal<User | null>(null);
  readonly activeOrgId = signal<string | null>(localStorage.getItem(ORG_KEY));
  readonly memberships = computed<Membership[]>(() => this.user()?.memberships ?? []);
  readonly activeMembership = computed(() => this.memberships().find(m => m.organization_id === this.activeOrgId()));
  readonly activeRole = computed(() => this.activeMembership()?.role ?? null);
  readonly isAuthenticated = computed(() => !!this.user());
  private refreshInFlight: Promise<boolean> | null = null;
  private sessionVersion = 0;

  constructor(private http: HttpClient, private router: Router) {}
  get accessToken(): string | null { return localStorage.getItem(ACCESS_KEY); }
  get refreshToken(): string | null { return localStorage.getItem(REFRESH_KEY); }
  private setTokens(tokens: TokenResponse) {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  }

  async login(email: string, password: string): Promise<void> {
    this.sessionVersion++;
    const tokens = await firstValueFrom(this.http.post<TokenResponse>(`${environment.apiBaseUrl}/auth/login`, { email: email.trim(), password }));
    this.setTokens(tokens);
    await this.loadCurrentUser();
  }
  async register(payload: { email: string; password: string; full_name: string; organization_name?: string; invitation_token?: string }): Promise<void> {
    await firstValueFrom(this.http.post(`${environment.apiBaseUrl}/auth/register`, payload));
    await this.login(payload.email, payload.password);
  }
  async loadCurrentUser(): Promise<void> {
    const version = this.sessionVersion;
    const user = await firstValueFrom(this.http.get<User>(`${environment.apiBaseUrl}/auth/me`));
    if (version !== this.sessionVersion) return;
    this.user.set(user);
    if (!user.memberships.some(m => m.organization_id === this.activeOrgId())) {
      const first = user.memberships[0]?.organization_id;
      this.activeOrgId.set(first ?? null);
      if (first) localStorage.setItem(ORG_KEY, first);
      else localStorage.removeItem(ORG_KEY);
    }
  }
  refreshAccessToken(): Promise<boolean> {
    if (this.refreshInFlight) return this.refreshInFlight;
    const refresh_token = this.refreshToken;
    const version = this.sessionVersion;
    if (!refresh_token) return Promise.resolve(false);
    const request = firstValueFrom(this.http.post<TokenResponse>(`${environment.apiBaseUrl}/auth/refresh`, { refresh_token }))
      .then(tokens => {
        if (version !== this.sessionVersion || this.refreshToken !== refresh_token) return false;
        this.setTokens(tokens);
        return true;
      }).catch(() => false).finally(() => { if (this.refreshInFlight === request) this.refreshInFlight = null; });
    this.refreshInFlight = request;
    return request;
  }
  setActiveOrg(orgId: string): void {
    if (!this.memberships().some(m => m.organization_id === orgId)) return;
    this.activeOrgId.set(orgId);
    localStorage.setItem(ORG_KEY, orgId);
  }
  switchOrganization(orgId: string): void {
    if (orgId === this.activeOrgId() || !this.memberships().some(m => m.organization_id === orgId)) return;
    this.setActiveOrg(orgId);
    // A new page clears every tenant-scoped view and pending conversation.
    window.location.assign('/dashboard');
  }
  logout(revoke = true): void {
    const refresh_token = this.refreshToken;
    const access_token = this.accessToken;
    this.sessionVersion++;
    this.refreshInFlight = null;
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(ORG_KEY);
    this.user.set(null);
    this.activeOrgId.set(null);
    if (revoke && refresh_token) {
      this.http.post(`${environment.apiBaseUrl}/auth/logout`, { refresh_token }, {
        headers: access_token ? { Authorization: `Bearer ${access_token}` } : {},
      }).subscribe({ error: () => undefined });
    }
    void this.router.navigate(['/login']);
  }
  hasAtLeastRole(minRole: Membership['role']): boolean {
    const rank: Record<string, number> = { viewer: 0, contributor: 1, content_owner: 2, org_admin: 3, platform_admin: 4 };
    const role = this.activeRole();
    return role !== null && rank[role] >= rank[minRole];
  }
}
