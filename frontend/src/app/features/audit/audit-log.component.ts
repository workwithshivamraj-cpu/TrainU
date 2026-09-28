import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { AuditService } from '../../core/api.services';
import { AuditLogEntry } from '../../core/models';

@Component({
  selector: 'app-audit-log',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-6">
      <div>
        <h1 class="text-xl font-semibold text-slate-900">Audit log</h1>
        <p class="text-sm text-slate-500">Login, invitations, uploads, approvals, deletions, role changes, and assistant activity.</p>
      </div>

      @if (loading()) {
        <p class="text-sm text-slate-500">Loading…</p>
      } @else if (entries().length === 0) {
        <div class="card p-10 text-center text-slate-500">No audit events recorded yet.</div>
      } @else {
        <div class="card overflow-hidden">
          <table class="w-full text-sm">
            <thead class="bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th class="text-left px-4 py-2">When</th>
                <th class="text-left px-4 py-2">Action</th>
                <th class="text-left px-4 py-2">Resource</th>
                <th class="text-left px-4 py-2">Description</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              @for (e of entries(); track e.id) {
                <tr>
                  <td class="px-4 py-2 text-slate-500 whitespace-nowrap">{{ e.created_at | date: 'short' }}</td>
                  <td class="px-4 py-2"><span class="badge bg-slate-100 text-slate-600">{{ e.action.replace('_',' ') }}</span></td>
                  <td class="px-4 py-2 text-slate-500">{{ e.resource_type }}</td>
                  <td class="px-4 py-2 text-slate-700">{{ e.description || '—' }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
})
export class AuditLogComponent implements OnInit {
  entries = signal<AuditLogEntry[]>([]);
  loading = signal(true);

  constructor(private auditService: AuditService) {}

  async ngOnInit() {
    this.entries.set(await this.auditService.list().catch(() => []));
    this.loading.set(false);
  }
}
