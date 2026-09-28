import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { OrganizationsService } from '../../core/api.services';
import { Organization } from '../../core/models';

@Component({
  selector: 'app-org-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="max-w-xl space-y-6">
      <div>
        <h1 class="text-xl font-semibold text-slate-900">Organization settings</h1>
        <p class="text-sm text-slate-500">Name, branding, and data retention for this organization.</p>
      </div>

      @if (org(); as o) {
        <form class="card p-6 space-y-4" (ngSubmit)="save()">
          <div>
            <label class="label" for="name">Organization name</label>
            <input class="input" id="name" name="name" [(ngModel)]="name" />
          </div>
          <div>
            <label class="label" for="logo">Logo URL</label>
            <input class="input" id="logo" name="logo" [(ngModel)]="logoUrl" placeholder="https://…" />
          </div>
          <div>
            <label class="label" for="retention">Retention period (days)</label>
            <input class="input" id="retention" name="retention" type="number" min="1" [(ngModel)]="retentionDays" />
            <p class="mt-1 text-xs text-slate-500">
              How long uploaded source content is retained before it's eligible for cleanup.
            </p>
          </div>
          <div class="text-sm text-slate-500">
            <p>Slug: <span class="font-mono">{{ o.slug }}</span></p>
            <p>Created: {{ o.created_at | date: 'medium' }}</p>
          </div>
          @if (saved()) {
            <p class="text-sm text-emerald-700">Saved.</p>
          }
          <button class="btn-primary" type="submit" [disabled]="saving()">{{ saving() ? 'Saving…' : 'Save changes' }}</button>
        </form>
      }
    </div>
  `,
})
export class OrgSettingsComponent implements OnInit {
  org = signal<Organization | null>(null);
  name = '';
  logoUrl = '';
  retentionDays = 365;
  saving = signal(false);
  saved = signal(false);

  constructor(private orgService: OrganizationsService) {}

  async ngOnInit() {
    const org = await this.orgService.getCurrent();
    this.org.set(org);
    this.name = org.name;
    this.logoUrl = org.logo_url ?? '';
    this.retentionDays = org.retention_days;
  }

  async save() {
    this.saving.set(true);
    this.saved.set(false);
    try {
      const updated = await this.orgService.update({
        name: this.name,
        logo_url: this.logoUrl || null,
        retention_days: this.retentionDays,
      });
      this.org.set(updated);
      this.saved.set(true);
    } finally {
      this.saving.set(false);
    }
  }
}
