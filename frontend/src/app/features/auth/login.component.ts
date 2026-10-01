import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { errorMessage } from '../../core/error-message';

@Component({
  selector: 'app-login', standalone: true, imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="min-h-screen auth-background flex flex-col p-6 sm:p-12">
      <a routerLink="/login" class="flex items-center gap-2.5 self-start font-semibold text-xl"><span class="h-9 w-9 rounded-xl bg-brand-700 text-white flex items-center justify-center text-lg font-extrabold tracking-[-.12em] pr-0.5" aria-hidden="true">t<span class="text-brand-200">u</span></span>TrainU.</a>
      <main class="w-full max-w-6xl mx-auto flex-1 grid lg:grid-cols-2 items-center gap-16 py-12">
        <section class="hidden lg:block">
          <p class="eyebrow mb-6">Your team's knowledge, in reach</p>
          <h1 class="text-6xl leading-[1.08] font-semibold tracking-tight text-slate-900">Less searching.<br><span class="text-brand-700">More knowing.</span></h1>
          <p class="text-lg leading-relaxed text-slate-500 mt-6 max-w-md">Bring your training videos and documents together. Ask a question. Go straight to the source.</p>
          <div class="mt-10 max-w-md rounded-2xl bg-white/80 border border-white p-6 shadow-sm">
            <div class="flex gap-3 items-center"><span class="h-8 w-8 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center">✧</span><p class="text-sm font-medium">How does our approval process work?</p></div>
            <div class="ml-11 mt-4 space-y-2" aria-hidden="true"><div class="bg-slate-100 h-2 rounded-full w-full"></div><div class="bg-slate-100 h-2 rounded-full w-4/5"></div></div>
            <p class="ml-11 mt-4 text-xs text-brand-700">Answers connected to approved training</p>
          </div>
        </section>
        <section class="w-full max-w-md mx-auto">
          <div class="card !border-white shadow-xl shadow-brand-900/5 p-7 sm:p-10">
            <p class="eyebrow mb-3">Welcome back</p><h2 class="text-3xl font-semibold">Sign in to TrainU</h2>
            <p class="mt-2 text-sm text-slate-500">A little clarity for your workday.</p>
            <form class="mt-8 space-y-5" (ngSubmit)="submit()" #form="ngForm">
              <div><label class="label" for="email">Work email</label><input class="input" id="email" name="email" type="email" required email [(ngModel)]="email" autocomplete="username" placeholder="you@company.com" /></div>
              <div><label class="label" for="password">Password</label><input class="input" id="password" name="password" type="password" required [(ngModel)]="password" autocomplete="current-password" /></div>
              @if (error()) { <p class="rounded-xl bg-red-50 p-3 text-sm text-red-700" role="alert">{{ error() }}</p> }
              <button type="submit" class="btn-primary w-full" [disabled]="loading() || form.invalid">{{ loading() ? 'Signing in…' : 'Sign in →' }}</button>
            </form>
            <p class="mt-6 text-sm text-slate-500 text-center">New here? <a routerLink="/register" class="font-semibold text-brand-700 hover:underline">Create a workspace</a></p>
          </div>
          <p class="mt-6 text-center text-xs text-slate-500 leading-relaxed">Invited by your team? Open the invitation link your administrator shared.</p>
        </section>
      </main>
      <footer class="flex justify-between text-xs text-slate-500"><span>TrainU · Knowledge that moves with you.</span><a routerLink="/guide" class="hover:underline">Help & documentation</a></footer>
    </div>
  `,
})
export class LoginComponent {
  email = ''; password = ''; loading = signal(false); error = signal<string | null>(null);
  constructor(private auth: AuthService, private router: Router, private route: ActivatedRoute) {}
  async submit() {
    if (this.loading() || !this.email.trim() || !this.password) return;
    this.error.set(null); this.loading.set(true);
    try {
      await this.auth.login(this.email, this.password);
      const target = this.route.snapshot.queryParamMap.get('returnUrl');
      await this.router.navigateByUrl(target && target.startsWith('/') && !target.startsWith('//') && !target.startsWith('/login') ? target : '/dashboard');
    } catch (e) { this.error.set(errorMessage(e, 'Unable to sign in. Check your email and password.')); }
    finally { this.loading.set(false); }
  }
}
