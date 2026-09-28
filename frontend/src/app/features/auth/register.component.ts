import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div class="w-full max-w-sm">
        <div class="text-center mb-8">
          <div class="mx-auto h-12 w-12 rounded-lg bg-brand-600 flex items-center justify-center text-white text-2xl font-bold">T</div>
          <h1 class="mt-4 text-2xl font-semibold text-slate-900">Create your organization</h1>
          <p class="mt-1 text-sm text-slate-500">You'll become the Organization Admin.</p>
        </div>

        <form class="card p-6 space-y-4" (ngSubmit)="submit()" #form="ngForm" novalidate>
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
            <input class="input" id="email" name="email" type="email" required [(ngModel)]="email" autocomplete="username" />
          </div>
          <div>
            <label class="label" for="password">Password</label>
            <input class="input" id="password" name="password" type="password" required minlength="8" [(ngModel)]="password" autocomplete="new-password" />
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
    this.error.set(null);
    this.loading.set(true);
    try {
      await this.auth.register({
        email: this.email,
        password: this.password,
        full_name: this.fullName,
        organization_name: this.organizationName,
      });
      await this.router.navigate(['/dashboard']);
    } catch (e: any) {
      this.error.set(e?.error?.detail ?? 'Unable to create your organization.');
    } finally {
      this.loading.set(false);
    }
  }
}
