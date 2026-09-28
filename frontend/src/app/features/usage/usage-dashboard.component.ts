import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { UsageService } from '../../core/api.services';
import { UsageSummary } from '../../core/models';

@Component({
  selector: 'app-usage-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-6">
      <div>
        <h1 class="text-xl font-semibold text-slate-900">Usage</h1>
        <p class="text-sm text-slate-500">Storage, processing, and engagement over the last 30 days.</p>
      </div>

      @if (usage(); as u) {
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div class="card p-4">
            <p class="text-xs uppercase tracking-wide text-slate-500">Stored video minutes</p>
            <p class="mt-1 text-2xl font-semibold">{{ u.total_stored_video_minutes | number: '1.0-1' }}</p>
          </div>
          <div class="card p-4">
            <p class="text-xs uppercase tracking-wide text-slate-500">Processed video minutes</p>
            <p class="mt-1 text-2xl font-semibold">{{ u.total_processed_video_minutes | number: '1.0-1' }}</p>
          </div>
          <div class="card p-4">
            <p class="text-xs uppercase tracking-wide text-slate-500">Questions asked</p>
            <p class="mt-1 text-2xl font-semibold">{{ u.total_questions_asked }}</p>
          </div>
          <div class="card p-4">
            <p class="text-xs uppercase tracking-wide text-slate-500">Active users</p>
            <p class="mt-1 text-2xl font-semibold">{{ u.active_users_last_30_days }}</p>
          </div>
        </div>

        <div class="card p-5">
          <h2 class="font-semibold text-slate-800 mb-3">Daily breakdown</h2>
          @if (u.daily.length === 0) {
            <p class="text-sm text-slate-500">No usage recorded yet.</p>
          } @else {
            <table class="w-full text-sm">
              <thead class="text-left text-xs uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th class="py-2">Date</th>
                  <th class="py-2">Stored min</th>
                  <th class="py-2">Processed min</th>
                  <th class="py-2">Questions</th>
                  <th class="py-2">Active users</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                @for (d of u.daily; track d.metric_date) {
                  <tr>
                    <td class="py-2">{{ d.metric_date }}</td>
                    <td class="py-2">{{ d.stored_video_minutes | number: '1.0-1' }}</td>
                    <td class="py-2">{{ d.processed_video_minutes | number: '1.0-1' }}</td>
                    <td class="py-2">{{ d.questions_asked }}</td>
                    <td class="py-2">{{ d.active_users }}</td>
                  </tr>
                }
              </tbody>
            </table>
          }
        </div>
      } @else {
        <p class="text-sm text-slate-500">Loading…</p>
      }
    </div>
  `,
})
export class UsageDashboardComponent implements OnInit {
  usage = signal<UsageSummary | null>(null);

  constructor(private usageService: UsageService) {}

  async ngOnInit() {
    this.usage.set(await this.usageService.summary());
  }
}
