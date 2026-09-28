import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { AssistantService } from '../../core/api.services';
import { FeedbackEntry } from '../../core/models';

@Component({
  selector: 'app-feedback',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-6">
      <div>
        <h1 class="text-xl font-semibold text-slate-900">Assistant feedback</h1>
        <p class="text-sm text-slate-500">Helpful / not-helpful ratings submitted by users on TrainU's answers.</p>
      </div>

      @if (loading()) {
        <p class="text-sm text-slate-500">Loading…</p>
      } @else if (entries().length === 0) {
        <div class="card p-10 text-center text-slate-500">No feedback submitted yet.</div>
      } @else {
        <div class="grid grid-cols-2 gap-4 mb-2">
          <div class="card p-4">
            <p class="text-xs uppercase tracking-wide text-slate-500">Helpful</p>
            <p class="mt-1 text-2xl font-semibold text-emerald-700">{{ helpfulCount() }}</p>
          </div>
          <div class="card p-4">
            <p class="text-xs uppercase tracking-wide text-slate-500">Not helpful</p>
            <p class="mt-1 text-2xl font-semibold text-red-700">{{ notHelpfulCount() }}</p>
          </div>
        </div>
        <div class="card divide-y divide-slate-100">
          @for (f of entries(); track f.id) {
            <div class="p-4 flex items-start justify-between gap-4">
              <div>
                <span class="badge" [ngClass]="f.rating === 'helpful' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'">
                  {{ f.rating === 'helpful' ? '👍 Helpful' : '👎 Not helpful' }}
                </span>
                @if (f.comment) {
                  <p class="mt-1 text-sm text-slate-700">{{ f.comment }}</p>
                }
              </div>
              <span class="text-xs text-slate-400 whitespace-nowrap">{{ f.created_at | date: 'short' }}</span>
            </div>
          }
        </div>
      }
    </div>
  `,
})
export class FeedbackComponent implements OnInit {
  entries = signal<FeedbackEntry[]>([]);
  loading = signal(true);

  constructor(private assistantService: AssistantService) {}

  async ngOnInit() {
    this.entries.set(await this.assistantService.listFeedback().catch(() => []));
    this.loading.set(false);
  }

  helpfulCount() {
    return this.entries().filter((e) => e.rating === 'helpful').length;
  }
  notHelpfulCount() {
    return this.entries().filter((e) => e.rating === 'not_helpful').length;
  }
}
