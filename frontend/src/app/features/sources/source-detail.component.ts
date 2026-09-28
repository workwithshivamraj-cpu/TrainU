import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { SourcesService } from '../../core/api.services';
import { SourceDetail, TranscriptChunk } from '../../core/models';

@Component({
  selector: 'app-source-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    @if (source(); as s) {
      <div class="space-y-6">
        <div>
          <a routerLink="/sources" class="text-sm text-brand-600 hover:text-brand-700">&larr; Sources</a>
          <div class="flex flex-wrap items-start justify-between gap-3 mt-1">
            <div>
              <h1 class="text-xl font-semibold text-slate-900">{{ s.title }}</h1>
              <p class="text-sm text-slate-500">{{ s.description }}</p>
            </div>
            <div class="flex items-center gap-2">
              <span class="badge" [ngClass]="statusClass(s.status)">{{ s.status.replace('_',' ') }}</span>
              @if (auth.hasAtLeastRole('content_owner')) {
                @if (s.status === 'awaiting_review') {
                  <button class="btn-primary" (click)="approve()">Approve</button>
                }
                @if (s.status !== 'archived') {
                  <button class="btn-secondary" (click)="archive()">Archive</button>
                }
              }
              @if (auth.hasAtLeastRole('org_admin') && s.status === 'archived') {
                <button class="btn-danger" (click)="remove()">Delete</button>
              }
            </div>
          </div>
        </div>

        @if (s.status === 'failed' && s.failure_reason) {
          <div class="card p-4 bg-red-50 border-red-200 text-red-700 text-sm">
            Processing failed: {{ s.failure_reason }}
          </div>
        }

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div class="lg:col-span-2 space-y-6">
            @if (s.source_type === 'video' && s.playback_url) {
              <div class="card p-4">
                <video class="w-full rounded-md bg-black aspect-video" controls [src]="s.playback_url"></video>
              </div>
            }

            <div class="card p-5">
              <h2 class="font-semibold text-slate-800 mb-3">Transcript / chunk viewer</h2>
              @if (chunks().length === 0) {
                <p class="text-sm text-slate-500">No chunks yet — processing may still be in progress.</p>
              }
              <div class="space-y-3">
                @for (c of chunks(); track c.id) {
                  <div class="border border-slate-200 rounded-md p-3">
                    <div class="flex items-center justify-between">
                      <span class="text-xs font-mono text-brand-700">{{ formatTime(c.start_seconds) }}–{{ formatTime(c.end_seconds) }}</span>
                      @if (auth.hasAtLeastRole('content_owner') && editingChunkId !== c.id) {
                        <button class="text-xs text-brand-600 hover:text-brand-700" (click)="startEdit(c)">Edit</button>
                      }
                    </div>
                    @if (editingChunkId === c.id) {
                      <textarea class="input mt-2" rows="3" [(ngModel)]="editText" [name]="'edit-' + c.id"></textarea>
                      <div class="mt-2 flex gap-2">
                        <button class="btn-primary text-xs" (click)="saveEdit(c)">Save</button>
                        <button class="btn-secondary text-xs" (click)="editingChunkId = null">Cancel</button>
                      </div>
                    } @else {
                      <p class="mt-1 text-sm text-slate-700">{{ c.text }}</p>
                      <p class="mt-1 text-xs text-slate-400">Topic: {{ c.topic }}</p>
                    }
                  </div>
                }
              </div>
            </div>
          </div>

          <div class="space-y-6">
            <div class="card p-5">
              <h2 class="font-semibold text-slate-800 mb-3">Metadata</h2>
              <dl class="text-sm space-y-2">
                <div class="flex justify-between"><dt class="text-slate-500">Type</dt><dd class="capitalize">{{ s.source_type }}</dd></div>
                <div class="flex justify-between"><dt class="text-slate-500">Version</dt><dd>{{ s.application_version || '—' }}</dd></div>
                <div class="flex justify-between"><dt class="text-slate-500">Environment</dt><dd class="capitalize">{{ s.environment || '—' }}</dd></div>
                <div class="flex justify-between"><dt class="text-slate-500">Feature tag</dt><dd>{{ s.feature_tag || '—' }}</dd></div>
                <div class="flex justify-between"><dt class="text-slate-500">Duration</dt><dd>{{ s.duration_seconds ? formatTime(s.duration_seconds) : '—' }}</dd></div>
                <div class="flex justify-between"><dt class="text-slate-500">Audience roles</dt><dd>{{ s.audience_roles.join(', ') || 'All' }}</dd></div>
                <div class="flex justify-between"><dt class="text-slate-500">Approved at</dt><dd>{{ s.approved_at ? (s.approved_at | date: 'short') : '—' }}</dd></div>
              </dl>
            </div>

            <div class="card p-5">
              <h2 class="font-semibold text-slate-800 mb-3">Processing jobs</h2>
              <ol class="space-y-2">
                @for (j of s.jobs; track j.id) {
                  <li class="text-sm flex items-center justify-between">
                    <span class="capitalize text-slate-700">{{ j.stage.replace('_',' ') }}</span>
                    <span class="badge" [ngClass]="jobStatusClass(j.status)">{{ j.status }}</span>
                  </li>
                }
                @if (!s.jobs.length) {
                  <p class="text-sm text-slate-500">No jobs recorded yet.</p>
                }
              </ol>
            </div>
          </div>
        </div>
      </div>
    } @else {
      <p class="text-sm text-slate-500">Loading…</p>
    }
  `,
})
export class SourceDetailComponent implements OnInit {
  source = signal<SourceDetail | null>(null);
  chunks = signal<TranscriptChunk[]>([]);
  editingChunkId: string | null = null;
  editText = '';

  constructor(
    public auth: AuthService,
    private route: ActivatedRoute,
    private router: Router,
    private sourcesService: SourcesService
  ) {}

  async ngOnInit() {
    await this.load();
  }

  async load() {
    const id = this.route.snapshot.paramMap.get('id')!;
    const [source, chunks] = await Promise.all([
      this.sourcesService.get(id),
      this.sourcesService.chunks(id).catch(() => []),
    ]);
    this.source.set(source);
    this.chunks.set(chunks);
  }

  startEdit(chunk: TranscriptChunk) {
    this.editingChunkId = chunk.id;
    this.editText = chunk.text;
  }

  async saveEdit(chunk: TranscriptChunk) {
    const s = this.source();
    if (!s) return;
    await this.sourcesService.updateChunk(s.id, chunk.id, { text: this.editText });
    this.editingChunkId = null;
    await this.load();
  }

  async approve() {
    const s = this.source();
    if (!s) return;
    await this.sourcesService.approve(s.id);
    await this.load();
  }

  async archive() {
    const s = this.source();
    if (!s) return;
    await this.sourcesService.archive(s.id);
    await this.load();
  }

  async remove() {
    const s = this.source();
    if (!s) return;
    await this.sourcesService.remove(s.id);
    await this.router.navigate(['/sources']);
  }

  formatTime(totalSeconds: number): string {
    const s = Math.max(0, Math.round(totalSeconds));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${r.toString().padStart(2, '0')}`;
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

  jobStatusClass(status: string): string {
    const map: Record<string, string> = {
      pending: 'bg-slate-100 text-slate-600',
      running: 'bg-blue-50 text-blue-700',
      succeeded: 'bg-emerald-50 text-emerald-700',
      failed: 'bg-red-50 text-red-700',
    };
    return map[status] ?? 'bg-slate-100 text-slate-600';
  }
}
