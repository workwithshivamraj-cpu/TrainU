import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { OrganizationsService } from '../../core/api.services';

@Component({
  selector: 'app-accept-invite',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div class="w-full max-w-sm">
        <div class="text-center mb-8">
          <div class="mx-auto h-12 w-12 rounded-lg bg-brand-600 flex items-center justify-center text-white text-2xl font-bold">T</div>
          <h1 class="mt-4 text-2xl font-semibold text-slate-900">Join your team on TrainU</h1>
          <p class="mt-1 text-sm text-slate-500">Sign in or create an account with the invited email to accept.</p>
        </div>

        <form class="card p-6 space-y-4" (ngSubmit)="signInThenAccept()" #form="ngForm" novalidate>
          <div>
            <label class="label" for="email">Email</label>
            <input class="input" id="email" name="email" type="email" required [(ngModel)]="email" />
          </div>
          <div>
            <label class="label" for="password">Password</label>
            <input class="input" id="password" name="password" type="password" required [(ngModel)]="password" />
          </div>
          <div>
            <label class="label" for="name">Full name (only needed if you don't have an account yet)</label>
            <input class="input" id="name" name="name" [(ngModel)]="fullName" />
          </div>

          @if (error()) {
            <p class="text-sm text-red-600" role="alert">{{ error() }}</p>
          }

          <div class="flex gap-2">
            <button type="button" class="btn-secondary flex-1" (click)="signInThenAccept()" [disabled]="loading()">Sign in &amp; accept</button>
            <button type="button" class="btn-primary flex-1" (click)="registerThenAccept()" [disabled]="loading()">Create account &amp; accept</button>
          </div>
        </form>
      </div>
    </div>
  `,
})
export class AcceptInviteComponent implements OnInit {
  token = '';
  email = '';
  password = '';
  fullName = '';
  loading = signal(false);
  error = signal<string | null>(null);

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private auth: AuthService,
    private orgService: OrganizationsService
  ) {}

  ngOnInit() {
    this.token = this.route.snapshot.queryParamMap.get('token') ?? '';
  }

  async signInThenAccept() {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.auth.login(this.email, this.password);
      await this.accept();
    } catch (e: any) {
      this.error.set(e?.error?.detail ?? 'Unable to sign in.');
    } finally {
      this.loading.set(false);
    }
  }

  async registerThenAccept() {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.auth.register({ email: this.email, password: this.password, full_name: this.fullName || this.email });
      await this.accept();
    } catch (e: any) {
      this.error.set(e?.error?.detail ?? 'Unable to create your account.');
    } finally {
      this.loading.set(false);
    }
  }

  private async accept() {
    if (!this.token) {
      this.error.set('Missing invitation token.');
      return;
    }
    await this.orgService.acceptInvitation(this.token);
    await this.auth.loadCurrentUser();
    const memberships = this.auth.memberships();
    if (memberships.length) {
      this.auth.setActiveOrg(memberships[memberships.length - 1].organization_id);
    }
    await this.router.navigate(['/dashboard']);
  }
}
