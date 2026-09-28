import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { ApplicationsService } from '../../core/api.services';
import { Application } from '../../core/models';

@Component({
  selector: 'app-application-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-xl font-semibold text-slate-900">Applications</h1>
          <p class="text-sm text-slate-500">The application catalog TrainU content is organized around.</p>
        </div>
        @if (auth.hasAtLeastRole('content_owner')) {
          <button class="btn-primary" (click)="showCreate.set(!showCreate())">
            {{ showCreate() ? 'Cancel' : '+ New application' }}
          </button>
        }
      </div>

      @if (showCreate()) {
        <form class="card p-5 grid grid-cols-1 md:grid-cols-2 gap-4" (ngSubmit)="create()">
          <div>
            <label class="label">Name</label>
            <input class="input" name="name" required [(ngModel)]="form.name" />
          </div>
          <div>
            <label class="label">Version</label>
            <input class="input" name="version" [(ngModel)]="form.version" placeholder="1.0.0" />
          </div>
          <div class="md:col-span-2">
            <label class="label">Description</label>
            <textarea class="input" name="description" rows="2" [(ngModel)]="form.description"></textarea>
          </div>
          <div>
            <label class="label">Environment</label>
            <select class="input" name="environment" [(ngModel)]="form.environment">
              <option value="development">Development</option>
              <option value="uat">UAT</option>
              <option value="production">Production</option>
            </select>
          </div>
          <div>
            <label class="label">Status</label>
            <select class="input" name="status" [(ngModel)]="form.status">
              <option value="active">Active</option>
              <option value="maintenance">Maintenance</option>
              <option value="retired">Retired</option>
            </select>
          </div>
          <div>
            <label class="label">Owning team</label>
            <input class="input" name="owning_team" [(ngModel)]="form.owning_team" />
          </div>
          <div>
            <label class="label">Support contact</label>
            <input class="input" name="support_contact" [(ngModel)]="form.support_contact" />
          </div>
          <div class="md:col-span-2">
            <label class="label">Features (comma-separated)</label>
            <input class="input" name="features" [(ngModel)]="featuresInput" />
          </div>
          <div class="md:col-span-2">
            <button type="submit" class="btn-primary" [disabled]="creating()">
              {{ creating() ? 'Creating…' : 'Create application' }}
            </button>
          </div>
        </form>
      }

      @if (loading()) {
        <p class="text-sm text-slate-500">Loading…</p>
      } @else if (applications().length === 0) {
        <div class="card p-10 text-center text-slate-500">
          <p>No applications yet. Content owners can create the first one.</p>
        </div>
      } @else {
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          @for (a of applications(); track a.id) {
            <a [routerLink]="['/applications', a.id]" class="card p-5 block hover:border-brand-300">
              <div class="flex items-start justify-between">
                <h3 class="font-semibold text-slate-900">{{ a.name }}</h3>
                <span class="badge" [ngClass]="statusClass(a.status)">{{ a.status }}</span>
              </div>
              <p class="mt-1 text-sm text-slate-500 line-clamp-2">{{ a.description }}</p>
              <div class="mt-3 flex flex-wrap gap-1 text-xs text-slate-500">
                <span class="badge bg-slate-100">v{{ a.version }}</span>
                <span class="badge bg-slate-100 capitalize">{{ a.environment }}</span>
                <span class="badge bg-slate-100">{{ a.modules.length }} modules</span>
              </div>
            </a>
          }
        </div>
      }
    </div>
  `,
})
export class ApplicationListComponent implements OnInit {
  applications = signal<Application[]>([]);
  loading = signal(true);
  showCreate = signal(false);
  creating = signal(false);
  featuresInput = '';
  form: Partial<Application> = {
    name: '',
    description: '',
    version: '1.0.0',
    environment: 'production',
    status: 'active',
    owning_team: '',
    support_contact: '',
  };

  constructor(public auth: AuthService, private applicationsService: ApplicationsService) {}

  async ngOnInit() {
    await this.reload();
  }

  async reload() {
    this.loading.set(true);
    this.applications.set(await this.applicationsService.list().catch(() => []));
    this.loading.set(false);
  }

  async create() {
    this.creating.set(true);
    try {
      const features = this.featuresInput
        .split(',')
        .map((f) => f.trim())
        .filter(Boolean);
      await this.applicationsService.create({ ...this.form, features });
      this.showCreate.set(false);
      this.form = { name: '', description: '', version: '1.0.0', environment: 'production', status: 'active', owning_team: '', support_contact: '' };
      this.featuresInput = '';
      await this.reload();
    } finally {
      this.creating.set(false);
    }
  }

  statusClass(status: string): string {
    const map: Record<string, string> = {
      active: 'bg-emerald-50 text-emerald-700',
      maintenance: 'bg-amber-50 text-amber-700',
      retired: 'bg-slate-100 text-slate-500',
    };
    return map[status] ?? 'bg-slate-100';
  }
}
