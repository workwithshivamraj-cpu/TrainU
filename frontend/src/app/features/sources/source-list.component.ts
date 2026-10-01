import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { errorMessage } from '../../core/error-message';
import { AuthService } from '../../core/auth.service';
import { SourcesService } from '../../core/api.services';
import { SourceSummary, SourceStatus } from '../../core/models';

@Component({
  selector: 'app-source-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="space-y-6">
      <div class="flex flex-wrap gap-3 items-center justify-between">
        <div>
          <h1 class="text-3xl font-semibold text-slate-900">Knowledge library</h1>
          <p class="text-sm text-slate-500">The videos and documents your team learns from.</p>
        </div>
        @if (auth.hasAtLeastRole('contributor')) {
          <a routerLink="/sources/upload" class="btn-primary">+ Upload source</a>
        }
      </div>

      <div class="flex flex-wrap gap-2">
        @for (s of statusFilters; track s.value) {
          <button
            class="badge"
            [ngClass]="statusFilter === s.value ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
            (click)="setFilter(s.value)"
          >{{ s.label }}</button>
        }
      </div>

      @if (error()) { <p class="notice" role="alert">{{ error() }} <button class="underline ml-2" (click)="reload()">Retry</button></p> }
      @if (loading()) {
        <p class="text-sm text-slate-500">Loading…</p>
      } @else if (sources().length === 0) {
        <div class="card p-10 text-center text-slate-500">
          <p>No sources match this filter yet.</p>
        </div>
      } @else {
        <div class="card overflow-x-auto">
          <table class="w-full min-w-[600px] text-sm">
            <thead class="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th class="text-left px-4 py-2">Title</th>
                <th class="text-left px-4 py-2">Type</th>
                <th class="text-left px-4 py-2">Status</th>
                <th class="text-left px-4 py-2">Version</th>
                <th class="text-left px-4 py-2">Updated</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (s of sources(); track s.id) {
                <tr class="hover:bg-slate-50">
                  <td class="px-4 py-2">
                    <a [routerLink]="['/sources', s.id]" class="font-medium text-slate-800 hover:text-brand-700">{{ s.title }}</a>
                    @if (s.status === 'failed' && s.failure_reason) {
                      <p class="text-xs text-red-600">{{ s.failure_reason }}</p>
                    }
                  </td>
                  <td class="px-4 py-2 capitalize text-slate-600">{{ s.source_type }}</td>
                  <td class="px-4 py-2"><span class="badge" [ngClass]="statusClass(s.status)">{{ s.status.replace('_',' ') }}</span></td>
                  <td class="px-4 py-2 text-slate-500">{{ s.application_version || '—' }}</td>
                  <td class="px-4 py-2 text-slate-500">{{ s.updated_at | date: 'short' }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
})
export class SourceListComponent implements OnInit {
  sources = signal<SourceSummary[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);
  private loadVersion = 0;
  statusFilter: SourceStatus | '' = '';

  statusFilters: { value: SourceStatus | ''; label: string }[] = [
    { value: '', label: 'All' },
    { value: 'awaiting_review', label: 'Awaiting review' },
    { value: 'approved', label: 'Approved' },
    { value: 'indexed', label: 'Indexed' },
    { value: 'processing', label: 'Processing' },
    { value: 'failed', label: 'Failed' },
    { value: 'archived', label: 'Archived' },
  ];

  constructor(public auth: AuthService, private sourcesService: SourcesService) {}

  async ngOnInit() {
    await this.reload();
  }

  async setFilter(status: SourceStatus | '') {
    this.statusFilter = status;
    await this.reload();
  }

  async reload() {
    const version = ++this.loadVersion; this.loading.set(true); this.error.set(null);
    try { const sources = await this.sourcesService.list(this.statusFilter ? { status: this.statusFilter } : {}); if (version === this.loadVersion) this.sources.set(sources); }
    catch (e) { if (version === this.loadVersion) this.error.set(errorMessage(e, 'The knowledge library could not be loaded.')); }
    finally { if (version === this.loadVersion) this.loading.set(false); }
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
