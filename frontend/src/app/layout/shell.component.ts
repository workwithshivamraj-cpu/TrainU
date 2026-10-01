import { CommonModule } from '@angular/common';
import { Component, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../core/auth.service';

interface NavItem { label: string; path: string; icon: string; minRole?: 'contributor' | 'content_owner' | 'org_admin'; }
@Component({
  selector: 'app-shell', standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RouterLinkActive, RouterOutlet],
  template: `
    <a href="#main-content" class="sr-only focus:not-sr-only focus:fixed focus:z-50 focus:top-3 focus:left-3 btn-primary">Skip to content</a>
    <div class="min-h-screen flex bg-[#f7f9f8]">
      @if (menuOpen()) { <button class="fixed inset-0 bg-slate-900/20 z-30 lg:hidden" aria-label="Close navigation" (click)="menuOpen.set(false)"></button> }
      <aside class="fixed inset-y-0 left-0 z-40 flex flex-col bg-white border-r border-slate-200/80 transition-all duration-200 lg:translate-x-0"
        [ngClass]="sidebarCollapsed() ? 'w-64 lg:w-20' : 'w-64'"
        [class.-translate-x-full]="!menuOpen()" aria-label="Primary navigation" id="primary-navigation">
        <a routerLink="/dashboard" aria-label="TrainU home" class="h-24 flex items-center gap-3" [ngClass]="sidebarCollapsed() ? 'lg:justify-center lg:px-2 px-7' : 'px-7'" (click)="menuOpen.set(false)">
          <svg class="h-9 w-9 shrink-0" viewBox="0 0 36 36" aria-hidden="true"><rect width="36" height="36" rx="12" fill="#08775d"/><path d="M9 11.5h10v3H15.5V25h-3V14.5H9v-3Z" fill="white"/><path d="M20 14.5h3v1.2c.9-1 2-1.5 3.5-1.5 2.8 0 4.5 2 4.5 5V25h-3v-5.3c0-1.7-.8-2.6-2.3-2.6-1.6 0-2.7 1.1-2.7 2.8V25h-3V14.5Z" fill="#d1fae5"/></svg>
          <span class="text-xl tracking-tight font-semibold" [ngClass]="sidebarCollapsed() ? 'lg:hidden' : ''">TrainU<span class="text-brand-600">.</span></span>
        </a>
        <div class="px-7 pb-3 text-[10px] font-semibold tracking-[.18em] uppercase text-slate-400" [ngClass]="sidebarCollapsed() ? 'lg:hidden' : ''">Your workspace</div>
        <nav class="flex-1 overflow-y-auto px-4 space-y-1" [ngClass]="sidebarCollapsed() ? 'lg:px-2' : ''">
          @for (item of visibleNavItems(); track item.path) {
            <a [routerLink]="item.path" routerLinkActive="bg-brand-50 text-brand-800" ariaCurrentWhenActive="page"
              class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
              [ngClass]="sidebarCollapsed() ? 'lg:justify-center' : ''" [attr.title]="sidebarCollapsed() ? item.label : null" (click)="menuOpen.set(false)">
              <svg class="h-[18px] w-[18px] shrink-0 text-current" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                @switch (item.icon) {
                  @case ('overview') { <rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/> }
                  @case ('ask') { <path d="M12 3.5 14 10l6.5 2-6.5 2-2 6.5L10 14l-6.5-2L10 10l2-6.5Z"/> }
                  @case ('apps') { <rect x="4" y="4" width="16" height="16" rx="2.5"/><path d="M8 8h8M8 12h8M8 16h5"/> }
                  @case ('library') { <path d="M5 4h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M7 4v16M11 8h5M11 12h5M11 16h4"/> }
                  @case ('usage') { <path d="M20 12a8 8 0 1 1-2.3-5.7"/><path d="M20 4v5h-5M12 7v5l3 2"/> }
                  @case ('feedback') { <path d="M20 11.5c0 4.2-3.6 7.5-8 7.5a9 9 0 0 1-3.7-.8L4 20l1.2-3.5A7.2 7.2 0 0 1 4 12c0-4.2 3.6-7.5 8-7.5s8 2.8 8 7Z"/><path d="M8 12h.01M12 12h.01M16 12h.01"/> }
                  @case ('people') { <circle cx="9" cy="8" r="3"/><path d="M3.5 20v-1.2A4.8 4.8 0 0 1 8.3 14h1.4a4.8 4.8 0 0 1 4.8 4.8V20M16 5.4a3 3 0 0 1 0 5.2m1 3.4a4.8 4.8 0 0 1 3.5 4.6V20"/> }
                  @case ('settings') { <circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1a1.8 1.8 0 1 1-2.5 2.5l-.1-.1a1.8 1.8 0 0 0-3 .9v.2a1.8 1.8 0 1 1-3.6 0v-.2a1.8 1.8 0 0 0-3-.9l-.1.1a1.8 1.8 0 1 1-2.5-2.5l.1-.1a1.8 1.8 0 0 0-.9-3h-.2a1.8 1.8 0 1 1 0-3.6h.2a1.8 1.8 0 0 0 .9-3l-.1-.1a1.8 1.8 0 1 1 2.5-2.5l.1.1a1.8 1.8 0 0 0 3-.9v-.2a1.8 1.8 0 1 1 3.6 0v.2a1.8 1.8 0 0 0 3 .9l.1-.1a1.8 1.8 0 1 1 2.5 2.5l-.1.1a1.8 1.8 0 0 0 .9 3h.2a1.8 1.8 0 1 1 0 3.6h-.2a1.8 1.8 0 0 0-.9 3Z"/> }
                  @case ('activity') { <path d="M4 6h16M4 12h16M4 18h16"/><circle cx="7" cy="6" r=".8" fill="currentColor"/><circle cx="7" cy="12" r=".8" fill="currentColor"/><circle cx="7" cy="18" r=".8" fill="currentColor"/> }
                  @default { <circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 4.7 1.2c-.8 1.2-2.2 1.3-2.2 3M12 17h.01"/> }
                }
              </svg><span [ngClass]="sidebarCollapsed() ? 'lg:sr-only' : ''">{{ item.label }}</span>
            </a>
          }
        </nav>
        <div class="m-4 rounded-2xl bg-brand-50 p-4" [ngClass]="sidebarCollapsed() ? 'lg:hidden' : ''">
          <svg class="h-5 w-5 text-brand-700" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m12 2 2.2 7.8L22 12l-7.8 2.2L12 22l-2.2-7.8L2 12l7.8-2.2L12 2Z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>
          <p class="mt-1 text-sm font-semibold text-brand-900">Knowledge, connected.</p>
          <p class="mt-1 text-xs text-brand-800 leading-relaxed">Turn your team's training into answers with sources you can check.</p>
          <a routerLink="/help" class="inline-block mt-3 text-xs font-semibold text-brand-800 hover:underline" (click)="menuOpen.set(false)">Explore the guides →</a>
        </div>
        <div class="px-7 py-4 text-[10px] uppercase tracking-widest text-slate-400 border-t border-slate-100" [ngClass]="sidebarCollapsed() ? 'lg:hidden' : ''">Built for everyday learning</div>
      </aside>
      <div class="flex-1 flex flex-col min-w-0" [ngClass]="sidebarCollapsed() ? 'lg:ml-20' : 'lg:ml-64'">
        <header class="min-h-20 bg-white/95 border-b border-slate-200/80 flex items-center justify-between px-4 sm:px-8 gap-3 sticky top-0 z-20">
          <div class="flex min-w-0 items-center gap-3">
            <button class="btn-secondary lg:hidden !p-2" aria-label="Toggle navigation" aria-controls="primary-navigation" [attr.aria-expanded]="menuOpen()" (click)="menuOpen.set(!menuOpen())"><svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true">@if (menuOpen()) { <path d="m6 6 12 12M18 6 6 18"/> } @else { <path d="M4 7h16M4 12h16M4 17h16"/> }</svg></button>
            <button class="hidden lg:inline-flex btn-secondary !p-2" type="button" [attr.aria-label]="sidebarCollapsed() ? 'Expand sidebar' : 'Collapse sidebar'" aria-controls="primary-navigation" [attr.aria-expanded]="!sidebarCollapsed()" (click)="toggleSidebar()"><svg class="h-4 w-4 transition-transform" [class.rotate-180]="sidebarCollapsed()" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m12.5 4-6 6 6 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
            <div class="min-w-0">
              <p class="hidden sm:block text-[10px] uppercase tracking-widest text-slate-400 mb-1">Workspace</p>
              @if (auth.memberships().length > 1) {
                <label for="org-switch" class="sr-only">Active organization</label>
                <select id="org-switch" class="input !py-1 !px-2 max-w-48" [ngModel]="auth.activeOrgId()" (ngModelChange)="auth.switchOrganization($event)" name="org">
                  @for (m of auth.memberships(); track m.organization_id) { <option [value]="m.organization_id">{{ m.organization_name }}</option> }
                </select>
              } @else { <p class="text-sm font-semibold truncate max-w-36 sm:max-w-none">{{ auth.activeMembership()?.organization_name || 'Your workspace' }}</p> }
            </div>
          </div>
          <div class="flex items-center gap-3 sm:gap-4">
            <span class="hidden md:inline-flex badge bg-slate-100 text-slate-600 capitalize">{{ roleLabel() }}</span>
            <div class="hidden sm:flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-brand-800 text-sm font-semibold" aria-hidden="true">{{ initials() }}</div>
            <div class="hidden xl:block text-sm font-medium">{{ auth.user()?.full_name }}</div>
            <button class="text-xs sm:text-sm font-medium text-slate-500 hover:text-slate-900 px-2 py-2" (click)="auth.logout()">Sign out</button>
          </div>
        </header>
        <main class="flex-1 p-4 sm:p-8 lg:p-10 max-w-[1600px] w-full mx-auto" id="main-content" tabindex="-1"><router-outlet></router-outlet></main>
      </div>
    </div>
  `,
})
export class ShellComponent {
  menuOpen = signal(false);
  sidebarCollapsed = signal(false);
  private allNavItems: NavItem[] = [
    { label: 'Overview', path: '/dashboard', icon: 'overview' },
    { label: 'Ask TrainU', path: '/assistant', icon: 'ask' },
    { label: 'Applications', path: '/applications', icon: 'apps' },
    { label: 'Knowledge library', path: '/sources', icon: 'library' },
    { label: 'Usage', path: '/usage', icon: 'usage' },
    { label: 'Feedback', path: '/feedback', icon: 'feedback' },
    { label: 'People & roles', path: '/admin/users', icon: 'people', minRole: 'org_admin' },
    { label: 'Workspace settings', path: '/admin/org-settings', icon: 'settings', minRole: 'org_admin' },
    { label: 'Activity log', path: '/admin/audit-log', icon: 'activity', minRole: 'org_admin' },
    { label: 'Help & documentation', path: '/help', icon: '?' },
  ];
  visibleNavItems = computed(() => this.allNavItems.filter(i => !i.minRole || this.auth.hasAtLeastRole(i.minRole)));
  roleLabel = computed(() => (this.auth.activeRole() ?? 'Member').replace(/_/g, ' '));
  initials = computed(() => (this.auth.user()?.full_name ?? 'You').split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase());
  constructor(public auth: AuthService) {
    try { this.sidebarCollapsed.set(localStorage.getItem('trainu.sidebarCollapsed') === 'true'); } catch { /* storage may be unavailable */ }
  }
  toggleSidebar() {
    const collapsed = !this.sidebarCollapsed();
    this.sidebarCollapsed.set(collapsed);
    try { localStorage.setItem('trainu.sidebarCollapsed', String(collapsed)); } catch { /* preference is session-local when storage is unavailable */ }
  }
}
