import { HttpClient } from '@angular/common/http';
import { Injectable, computed, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';
import { Membership, User } from './models';

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

const ACCESS_KEY = 'trainu_access_token';
const REFRESH_KEY = 'trainu_refresh_token';
const ORG_KEY = 'trainu_active_org';

@Injectable({ providedIn: 'root' })
export class AuthService {
  readonly user = signal<User | null>(null);
  readonly activeOrgId = signal<string | null>(localStorage.getItem(ORG_KEY));
  readonly memberships = computed<Membership[]>(() => this.user()?.memberships ?? []);
  readonly activeMembership = computed<Membership | undefined>(() =>
    this.memberships().find((m) => m.organization_id === this.activeOrgId())
  );
  readonly activeRole = computed(() => this.activeMembership()?.role ?? null);
  readonly isAuthenticated = computed(() => !!this.user());

  constructor(private http: HttpClient, private router: Router) {}

  get accessToken(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  }
  get refreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  }

  private setTokens(tokens: TokenResponse) {
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  }

  async login(email: string, password: string): Promise<void> {
    const tokens = await firstValueFrom(
      this.http.post<TokenResponse>(`${environment.apiBaseUrl}/auth/login`, { email, password })
    );
    this.setTokens(tokens);
    await this.loadCurrentUser();
  }

  async register(payload: {
    email: string;
    password: string;
    full_name: string;
    organization_name?: string;
    invitation_token?: string;
  }): Promise<void> {
    await firstValueFrom(this.http.post(`${environment.apiBaseUrl}/auth/register`, payload));
    await this.login(payload.email, payload.password);
  }

  async loadCurrentUser(): Promise<void> {
    const user = await firstValueFrom(this.http.get<User>(`${environment.apiBaseUrl}/auth/me`));
    this.user.set(user);
    if (!this.activeOrgId() && user.memberships.length > 0) {
      this.setActiveOrg(user.memberships[0].organization_id);
    }
  }

  async refreshAccessToken(): Promise<boolean> {
    const refresh_token = this.refreshToken;
    if (!refresh_token) return false;
    try {
      const tokens = await firstValueFrom(
        this.http.post<TokenResponse>(`${environment.apiBaseUrl}/auth/refresh`, { refresh_token })
      );
      this.setTokens(tokens);
      return true;
    } catch {
      return false;
    }
  }

  setActiveOrg(orgId: string): void {
    this.activeOrgId.set(orgId);
    localStorage.setItem(ORG_KEY, orgId);
  }

  logout(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(ORG_KEY);
    this.user.set(null);
    this.activeOrgId.set(null);
    this.router.navigate(['/login']);
  }

  hasAtLeastRole(minRole: Membership['role']): boolean {
    const rank: Record<string, number> = {
      viewer: 0,
      contributor: 1,
      content_owner: 2,
      org_admin: 3,
      platform_admin: 4,
    };
    const role = this.activeRole();
    if (!role) return false;
    return rank[role] >= rank[minRole];
  }
}
