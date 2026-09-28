import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';
import { roleGuard } from './core/role.guard';
import { ShellComponent } from './layout/shell.component';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'register',
    loadComponent: () => import('./features/auth/register.component').then((m) => m.RegisterComponent),
  },
  {
    path: 'accept-invite',
    loadComponent: () =>
      import('./features/auth/accept-invite.component').then((m) => m.AcceptInviteComponent),
  },
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadComponent: () => import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'assistant',
        loadComponent: () => import('./features/assistant/assistant.component').then((m) => m.AssistantComponent),
      },
      {
        path: 'applications',
        loadComponent: () =>
          import('./features/applications/application-list.component').then((m) => m.ApplicationListComponent),
      },
      {
        path: 'applications/:id',
        loadComponent: () =>
          import('./features/applications/application-detail.component').then((m) => m.ApplicationDetailComponent),
      },
      {
        path: 'sources',
        loadComponent: () => import('./features/sources/source-list.component').then((m) => m.SourceListComponent),
      },
      {
        path: 'sources/upload',
        loadComponent: () =>
          import('./features/sources/source-upload.component').then((m) => m.SourceUploadComponent),
      },
      {
        path: 'sources/:id',
        loadComponent: () =>
          import('./features/sources/source-detail.component').then((m) => m.SourceDetailComponent),
      },
      {
        path: 'usage',
        loadComponent: () =>
          import('./features/usage/usage-dashboard.component').then((m) => m.UsageDashboardComponent),
      },
      {
        path: 'feedback',
        loadComponent: () => import('./features/feedback/feedback.component').then((m) => m.FeedbackComponent),
      },
      {
        path: 'admin/users',
        canActivate: [roleGuard('org_admin')],
        loadComponent: () => import('./features/admin/users.component').then((m) => m.UsersComponent),
      },
      {
        path: 'admin/org-settings',
        canActivate: [roleGuard('org_admin')],
        loadComponent: () =>
          import('./features/admin/org-settings.component').then((m) => m.OrgSettingsComponent),
      },
      {
        path: 'admin/audit-log',
        canActivate: [roleGuard('org_admin')],
        loadComponent: () => import('./features/audit/audit-log.component').then((m) => m.AuditLogComponent),
      },
    ],
  },
  { path: '**', redirectTo: 'dashboard' },
];
