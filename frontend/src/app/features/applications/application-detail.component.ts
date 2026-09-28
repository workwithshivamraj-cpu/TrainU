import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { ApplicationsService, SourcesService } from '../../core/api.services';
import { Application, SourceSummary } from '../../core/models';

@Component({
  selector: 'app-application-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    @if (application(); as a) {
      <div class="space-y-6">
        <div>
          <a routerLink="/applications" class="text-sm text-brand-600 hover:text-brand-700">&larr; Applications</a>
          <div class="flex items-start justify-between mt-1">
            <div>
              <h1 class="text-xl font-semibold text-slate-900">{{ a.name }}</h1>
              <p class="text-sm text-slate-500">{{ a.description }}</p>
            </div>
            <span class="badge bg-slate-100">v{{ a.version }}</span>
          </div>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="card p-4">
            <p class="text-xs uppercase text-slate-500">Environment</p>
            <p class="mt-1 font-medium capitalize">{{ a.environment }}</p>
          </div>
          <div class="card p-4">
            <p class="text-xs uppercase text-slate-500">Status</p>
            <p class="mt-1 font-medium capitalize">{{ a.status }}</p>
          </div>
          <div class="card p-4">
            <p class="text-xs uppercase text-slate-500">Owning team</p>
            <p class="mt-1 font-medium">{{ a.owning_team || '—' }}</p>
          </div>
          <div class="card p-4">
            <p class="text-xs uppercase text-slate-500">Support contact</p>
            <p class="mt-1 font-medium">{{ a.support_contact || '—' }}</p>
          </div>
        </div>

        <div class="card p-5">
          <h2 class="font-semibold text-slate-800 mb-2">Features</h2>
          <div class="flex flex-wrap gap-2">
            @for (f of a.features; track f) {
              <span class="badge bg-brand-50 text-brand-700">{{ f }}</span>
            }
            @if (!a.features.length) {
              <p class="text-sm text-slate-500">No features listed.</p>
            }
          </div>
        </div>

        <div class="card p-5">
          <div class="flex items-center justify-between mb-2">
            <h2 class="font-semibold text-slate-800">Modules</h2>
          </div>
          @if (a.modules.length === 0) {
            <p class="text-sm text-slate-500">No modules defined yet.</p>
          }
          <div class="divide-y divide-slate-100">
            @for (m of a.modules; track m.id) {
              <div class="py-2">
                <p class="font-medium text-slate-800 text-sm">{{ m.name }}</p>
                <p class="text-xs text-slate-500">{{ m.description }}</p>
              </div>
            }
          </div>

          @if (auth.hasAtLeastRole('content_owner')) {
            <form class="mt-4 flex gap-2" (ngSubmit)="addModule()">
              <input class="input" placeholder="New module name" name="moduleName" [(ngModel)]="newModuleName" />
              <button class="btn-secondary shrink-0" type="submit" [disabled]="!newModuleName.trim()">Add module</button>
            </form>
          }
        </div>

        <div class="card p-5">
          <div class="flex items-center justify-between mb-2">
            <h2 class="font-semibold text-slate-800">Sources for this application</h2>
            <a [routerLink]="['/sources/upload']" [queryParams]="{ applicationId: a.id }" class="text-sm text-brand-600 hover:text-brand-700">Upload source</a>
          </div>
          @if (sources().length === 0) {
            <p class="text-sm text-slate-500">No sources yet.</p>
          } @else {
            <ul class="divide-y divide-slate-100">
              @for (s of sources(); track s.id) {
                <li class="py-2 flex items-center justify-between text-sm">
                  <a [routerLink]="['/sources', s.id]" class="text-slate-800 hover:text-brand-700">{{ s.title }}</a>
                  <span class="badge bg-slate-100">{{ s.status.replace('_',' ') }}</span>
                </li>
              }
            </ul>
          }
        </div>
      </div>
    } @else {
      <p class="text-sm text-slate-500">Loading…</p>
    }
  `,
})
export class ApplicationDetailComponent implements OnInit {
  application = signal<Application | null>(null);
  sources = signal<SourceSummary[]>([]);
  newModuleName = '';

  constructor(
    public auth: AuthService,
    private route: ActivatedRoute,
    private applicationsService: ApplicationsService,
    private sourcesService: SourcesService
  ) {}

  async ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id')!;
    await this.load(id);
  }

  async load(id: string) {
    const [app, sources] = await Promise.all([
      this.applicationsService.get(id),
      this.sourcesService.list({ application_id: id }),
    ]);
    this.application.set(app);
    this.sources.set(sources);
  }

  async addModule() {
    const app = this.application();
    if (!app || !this.newModuleName.trim()) return;
    await this.applicationsService.addModule(app.id, { name: this.newModuleName.trim(), description: '', features: [] });
    this.newModuleName = '';
    await this.load(app.id);
  }
}
