import { CommonModule } from '@angular/common';
import { Component, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../core/auth.service';

interface NavItem {
  label: string;
  path: string;
  icon: string;
  minRole?: 'contributor' | 'content_owner' | 'org_admin';
}

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RouterLinkActive, RouterOutlet],
  template: `
    <div class="min-h-screen flex bg-slate-50">
      <!-- Left navigation -->
      <aside class="w-64 shrink-0 bg-slate-900 text-slate-200 flex flex-col" aria-label="Primary navigation">
        <div class="h-16 flex items-center gap-2 px-5 border-b border-slate-800">
          <div class="h-8 w-8 rounded-md bg-brand-500 flex items-center justify-center font-bold text-white">T</div>
          <span class="text-lg font-semibold text-white">TrainU</span>
        </div>
        <nav class="flex-1 overflow-y-auto py-4 px-2 space-y-0.5">
          @for (item of visibleNavItems(); track item.path) {
            <a
              [routerLink]="item.path"
              routerLinkActive="bg-slate-800 text-white"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
            >
              <span class="w-5 text-center" aria-hidden="true">{{ item.icon }}</span>
              {{ item.label }}
            </a>
          }
        </nav>
        <div class="p-3 border-t border-slate-800 text-xs text-slate-400">
          Ask TrainU. Learn directly from your team's approved training knowledge.
        </div>
      </aside>

      <div class="flex-1 flex flex-col min-w-0">
        <!-- Top bar -->
        <header class="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 gap-4">
          <div class="min-w-0">
            <label for="org-switch" class="sr-only">Active organization</label>
            @if (auth.memberships().length > 1) {
              <select
                id="org-switch"
                class="input py-1.5 text-sm max-w-xs"
                [ngModel]="auth.activeOrgId()"
                (ngModelChange)="auth.setActiveOrg($event)"
                name="org"
              >
                @for (m of auth.memberships(); track m.organization_id) {
                  <option [value]="m.organization_id">{{ m.organization_name }}</option>
                }
              </select>
            } @else {
              <span class="text-sm font-medium text-slate-700 truncate">{{
                auth.activeMembership()?.organization_name || 'TrainU'
              }}</span>
            }
          </div>
          <div class="flex items-center gap-3">
            <span class="badge bg-brand-50 text-brand-700 capitalize">{{ roleLabel() }}</span>
            <div class="text-right hidden sm:block">
              <div class="text-sm font-medium text-slate-800">{{ auth.user()?.full_name }}</div>
              <div class="text-xs text-slate-500">{{ auth.user()?.email }}</div>
            </div>
            <button class="btn-secondary text-sm" (click)="auth.logout()">Sign out</button>
          </div>
        </header>

        <main class="flex-1 overflow-y-auto p-6" id="main-content">
          <router-outlet></router-outlet>
        </main>
      </div>
    </div>
  `,
})
export class ShellComponent {
  private allNavItems: NavItem[] = [
    { label: 'Dashboard', path: '/dashboard', icon: '▦' },
    { label: 'Ask TrainU', path: '/assistant', icon: '✦' },
    { label: 'Applications', path: '/applications', icon: '⌘' },
    { label: 'Sources', path: '/sources', icon: '▶' },
    { label: 'Usage', path: '/usage', icon: '≡' },
    { label: 'Feedback', path: '/feedback', icon: '★' },
    { label: 'Users & Roles', path: '/admin/users', icon: '●', minRole: 'org_admin' },
    { label: 'Org Settings', path: '/admin/org-settings', icon: '⚙', minRole: 'org_admin' },
    { label: 'Audit Log', path: '/admin/audit-log', icon: '☷', minRole: 'org_admin' },
  ];

  visibleNavItems = computed(() =>
    this.allNavItems.filter((item) => !item.minRole || this.auth.hasAtLeastRole(item.minRole))
  );

  roleLabel = computed(() => (this.auth.activeRole() ?? '').replace('_', ' '));

  constructor(public auth: AuthService) {}
}
