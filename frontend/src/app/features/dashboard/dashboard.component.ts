import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApplicationsService, AssistantService, SourcesService, UsageService } from '../../core/api.services';
import { Application, SourceSummary, UsageSummary } from '../../core/models';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="space-y-6">
      <div>
        <h1 class="text-xl font-semibold text-slate-900">Dashboard</h1>
        <p class="text-sm text-slate-500">Welcome back, {{ auth.user()?.full_name }}.</p>
      </div>

      @if (loading()) {
        <p class="text-sm text-slate-500">Loading…</p>
      } @else {
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div class="card p-4">
            <p class="text-xs uppercase tracking-wide text-slate-500">Stored video minutes</p>
            <p class="mt-1 text-2xl font-semibold text-slate-900">{{ (usage?.total_stored_video_minutes ?? 0) | number: '1.0-1' }}</p>
          </div>
          <div class="card p-4">
            <p class="text-xs uppercase tracking-wide text-slate-500">Processed video minutes</p>
            <p class="mt-1 text-2xl font-semibold text-slate-900">{{ (usage?.total_processed_video_minutes ?? 0) | number: '1.0-1' }}</p>
          </div>
          <div class="card p-4">
            <p class="text-xs uppercase tracking-wide text-slate-500">Questions asked (30d)</p>
            <p class="mt-1 text-2xl font-semibold text-slate-900">{{ usage?.total_questions_asked ?? 0 }}</p>
          </div>
          <div class="card p-4">
            <p class="text-xs uppercase tracking-wide text-slate-500">Active users (30d)</p>
            <p class="mt-1 text-2xl font-semibold text-slate-900">{{ usage?.active_users_last_30_days ?? 0 }}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div class="card p-5 lg:col-span-2">
            <div class="flex items-center justify-between mb-3">
              <h2 class="font-semibold text-slate-800">Source processing status</h2>
              <a routerLink="/sources" class="text-sm text-brand-600 hover:text-brand-700">View all</a>
            </div>
            @if (sources().length === 0) {
              <p class="text-sm text-slate-500">No sources uploaded yet.</p>
            } @else {
              <table class="w-full text-sm">
                <thead>
                  <tr class="text-left text-xs uppercase text-slate-500 border-b border-slate-200">
                    <th class="py-2 pr-2">Title</th>
                    <th class="py-2 pr-2">Type</th>
                    <th class="py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  @for (s of sources(); track s.id) {
                    <tr class="border-b border-slate-100 last:border-0">
                      <td class="py-2 pr-2 text-slate-800">{{ s.title }}</td>
                      <td class="py-2 pr-2 text-slate-500 capitalize">{{ s.source_type }}</td>
                      <td class="py-2">
                        <span class="badge" [ngClass]="statusClass(s.status)">{{ s.status.replace('_',' ') }}</span>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            }
          </div>

          <div class="card p-5">
            <h2 class="font-semibold text-slate-800 mb-3">Quick actions</h2>
            <div class="space-y-2">
              <a routerLink="/assistant" class="btn-primary w-full">Ask TrainU</a>
              @if (auth.hasAtLeastRole('content_owner')) {
                <a routerLink="/sources/upload" class="btn-secondary w-full">Upload a source</a>
              }
              <a routerLink="/applications" class="btn-secondary w-full">Manage applications</a>
            </div>
            <div class="mt-5 pt-4 border-t border-slate-200">
              <p class="text-xs uppercase tracking-wide text-slate-500 mb-2">Applications</p>
              @for (a of applications(); track a.id) {
                <div class="flex items-center justify-between py-1 text-sm">
                  <span class="text-slate-700">{{ a.name }}</span>
                  <span class="text-slate-400">v{{ a.version }}</span>
                </div>
              }
            </div>
          </div>
        </div>
      }
    </div>
  `,
})
export class DashboardComponent implements OnInit {
  loading = signal(true);
  usage: UsageSummary | null = null;
  sources = signal<SourceSummary[]>([]);
  applications = signal<Application[]>([]);

  constructor(
    public auth: AuthService,
    private usageService: UsageService,
    private sourcesService: SourcesService,
    private applicationsService: ApplicationsService
  ) {}

  async ngOnInit() {
    const [usage, sources, applications] = await Promise.all([
      this.usageService.summary().catch(() => null),
      this.sourcesService.list().catch(() => []),
      this.applicationsService.list().catch(() => []),
    ]);
    this.usage = usage;
    this.sources.set(sources.slice(0, 6));
    this.applications.set(applications);
    this.loading.set(false);
  }

  statusClass(status: string): string {
    const map: Record<string, string> = {
      uploaded: 'bg-slate-100 text-slate-600',
      queued: 'bg-slate-100 text-slate-600',
      processing: 'bg-blue-50 text-blue-700',
      awaiting_review: 'bg-amber-50 text-amber-700',
      approved: 'bg-emerald-50 text-emerald-700',
      indexed: 'bg-emerald-50 text-emerald-700',
      failed: 'bg-red-50 text-red-700',
      archived: 'bg-slate-100 text-slate-500',
    };
    return map[status] ?? 'bg-slate-100 text-slate-600';
  }
}
