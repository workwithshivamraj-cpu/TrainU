import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { errorMessage } from '../../core/error-message';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="min-h-screen flex items-center justify-center auth-background px-4 py-12">
      <div class="w-full max-w-md">
        <div class="text-center mb-8">
          <div class="mx-auto h-12 w-12 rounded-xl bg-brand-700 flex items-center justify-center text-white text-2xl font-extrabold tracking-[-.12em] pr-0.5" aria-hidden="true">t<span class="text-brand-200">u</span></div>
          <h1 class="mt-4 text-2xl font-semibold text-slate-900">Create your workspace</h1>
          <p class="mt-1 text-sm text-slate-500">Bring your team's training together. You'll be the workspace admin.</p>
        </div>

        <form class="card p-7 sm:p-9 space-y-4" (ngSubmit)="submit()" #form="ngForm" novalidate>
          <div>
            <label class="label" for="org">Organization name</label>
            <input class="input" id="org" name="org" required [(ngModel)]="organizationName" placeholder="Acme Inc" />
          </div>
          <div>
            <label class="label" for="name">Your full name</label>
            <input class="input" id="name" name="name" required [(ngModel)]="fullName" />
          </div>
          <div>
            <label class="label" for="email">Email</label>
            <input class="input" id="email" name="email" type="email" required email [(ngModel)]="email" autocomplete="username" />
          </div>
          <div>
            <label class="label" for="password">Password</label>
            <input class="input" id="password" name="password" type="password" required minlength="8" maxlength="128" [(ngModel)]="password" autocomplete="new-password" />
            <p class="mt-1 text-xs text-slate-500">At least 8 characters.</p>
          </div>

          @if (error()) {
            <p class="text-sm text-red-600" role="alert">{{ error() }}</p>
          }

          <button type="submit" class="btn-primary w-full" [disabled]="loading() || form.invalid">
            {{ loading() ? 'Creating…' : 'Create organization' }}
          </button>
        </form>

        <p class="mt-6 text-center text-sm text-slate-500">
          Already have an account?
          <a routerLink="/login" class="font-medium text-brand-600 hover:text-brand-700">Sign in</a>
        </p>
      </div>
    </div>
  `,
})
export class RegisterComponent {
  organizationName = '';
  fullName = '';
  email = '';
  password = '';
  loading = signal(false);
  error = signal<string | null>(null);

  constructor(private auth: AuthService, private router: Router) {}

  async submit() {
    if (this.loading()) return;
    this.error.set(null);
    this.loading.set(true);
    try {
      await this.auth.register({
        email: this.email.trim(),
        password: this.password,
        full_name: this.fullName.trim(),
        organization_name: this.organizationName.trim(),
      });
      await this.router.navigate(['/dashboard']);
    } catch (e: any) {
      this.error.set(errorMessage(e, 'Unable to create your organization.'));
    } finally {
      this.loading.set(false);
    }
  }
}
