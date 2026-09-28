import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div class="w-full max-w-sm">
        <div class="text-center mb-8">
          <div class="mx-auto h-12 w-12 rounded-lg bg-brand-600 flex items-center justify-center text-white text-2xl font-bold">T</div>
          <h1 class="mt-4 text-2xl font-semibold text-slate-900">Sign in to TrainU</h1>
          <p class="mt-1 text-sm text-slate-500">Ask TrainU. Learn directly from your team's approved training knowledge.</p>
        </div>

        <form class="card p-6 space-y-4" (ngSubmit)="submit()" #form="ngForm" novalidate>
          <div>
            <label class="label" for="email">Email</label>
            <input class="input" id="email" name="email" type="email" required [(ngModel)]="email" autocomplete="username" />
          </div>
          <div>
            <label class="label" for="password">Password</label>
            <input class="input" id="password" name="password" type="password" required [(ngModel)]="password" autocomplete="current-password" />
          </div>

          @if (error()) {
            <p class="text-sm text-red-600" role="alert">{{ error() }}</p>
          }

          <button type="submit" class="btn-primary w-full" [disabled]="loading() || form.invalid">
            {{ loading() ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>

        <p class="mt-6 text-center text-sm text-slate-500">
          New to TrainU?
          <a routerLink="/register" class="font-medium text-brand-600 hover:text-brand-700">Create an organization</a>
        </p>

        <div class="mt-6 card p-4 text-xs text-slate-500">
          <p class="font-medium text-slate-700 mb-1">Demo credentials</p>
          <p>owner&#64;portfolioteam.example / TrainU_Demo123!</p>
          <p>viewer&#64;portfolioteam.example / TrainU_Demo123!</p>
        </div>
      </div>
    </div>
  `,
})
export class LoginComponent {
  email = '';
  password = '';
  loading = signal(false);
  error = signal<string | null>(null);

  constructor(private auth: AuthService, private router: Router) {}

  async submit() {
    this.error.set(null);
    this.loading.set(true);
    try {
      await this.auth.login(this.email, this.password);
      await this.router.navigate(['/dashboard']);
    } catch (e: any) {
      this.error.set(e?.error?.detail ?? 'Unable to sign in. Check your email and password.');
    } finally {
      this.loading.set(false);
    }
  }
}
