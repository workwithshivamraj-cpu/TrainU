import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ApplicationsService, SourcesService } from '../../core/api.services';
import { Application } from '../../core/models';

@Component({
  selector: 'app-source-upload',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="max-w-2xl space-y-6">
      <div>
        <h1 class="text-xl font-semibold text-slate-900">Upload a source</h1>
        <p class="text-sm text-slate-500">
          Upload a KT/training video (mp4, mov, m4v, webm) or a document (PDF, DOCX, Markdown, or plain text).
          It will be processed in the background and must be approved before it's searchable.
        </p>
      </div>

      <form class="card p-6 space-y-4" (ngSubmit)="submit()">
        <div>
          <label class="label" for="file">File</label>
          <input class="input" id="file" type="file" (change)="onFile($event)" required
            accept=".mp4,.mov,.m4v,.webm,.pdf,.docx,.md,.txt" />
          <p class="mt-1 text-xs text-slate-500">Max 1GB for video, 50MB for documents.</p>
        </div>
        <div>
          <label class="label" for="title">Title</label>
          <input class="input" id="title" name="title" required [(ngModel)]="title" />
        </div>
        <div>
          <label class="label" for="description">Description</label>
          <textarea class="input" id="description" name="description" rows="2" [(ngModel)]="description"></textarea>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label" for="application">Application</label>
            <select class="input" id="application" name="application" [(ngModel)]="applicationId">
              <option [ngValue]="null">None</option>
              @for (a of applications(); track a.id) {
                <option [ngValue]="a.id">{{ a.name }}</option>
              }
            </select>
          </div>
          <div>
            <label class="label" for="feature">Feature tag</label>
            <input class="input" id="feature" name="feature" [(ngModel)]="featureTag" placeholder="e.g. client-account-creation" />
          </div>
          <div>
            <label class="label" for="version">Application version</label>
            <input class="input" id="version" name="version" [(ngModel)]="applicationVersion" placeholder="e.g. 3.4.1" />
          </div>
          <div>
            <label class="label" for="env">Environment</label>
            <select class="input" id="env" name="env" [(ngModel)]="environmentValue">
              <option [ngValue]="null">Not specified</option>
              <option value="development">Development</option>
              <option value="uat">UAT</option>
              <option value="production">Production</option>
            </select>
          </div>
        </div>
        <div>
          <label class="label" for="roles">Audience roles (comma-separated)</label>
          <input class="input" id="roles" name="roles" [(ngModel)]="audienceRoles" placeholder="contributor, content_owner" />
        </div>

        @if (error()) {
          <p class="text-sm text-red-600" role="alert">{{ error() }}</p>
        }

        <button type="submit" class="btn-primary" [disabled]="uploading() || !file">
          {{ uploading() ? 'Uploading…' : 'Upload and process' }}
        </button>
      </form>
    </div>
  `,
})
export class SourceUploadComponent implements OnInit {
  applications = signal<Application[]>([]);
  file: File | null = null;
  title = '';
  description = '';
  applicationId: string | null = null;
  featureTag = '';
  applicationVersion = '';
  environmentValue: string | null = null;
  audienceRoles = '';
  uploading = signal(false);
  error = signal<string | null>(null);

  constructor(
    private applicationsService: ApplicationsService,
    private sourcesService: SourcesService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  async ngOnInit() {
    this.applications.set(await this.applicationsService.list().catch(() => []));
    const qp = this.route.snapshot.queryParamMap.get('applicationId');
    if (qp) this.applicationId = qp;
  }

  onFile(event: Event) {
    const input = event.target as HTMLInputElement;
    this.file = input.files?.[0] ?? null;
    if (this.file && !this.title) {
      this.title = this.file.name.replace(/\.[^.]+$/, '');
    }
  }

  async submit() {
    if (!this.file) return;
    this.error.set(null);
    this.uploading.set(true);
    try {
      const form = new FormData();
      form.append('file', this.file);
      form.append('title', this.title);
      form.append('description', this.description);
      if (this.applicationId) form.append('application_id', this.applicationId);
      form.append('feature_tag', this.featureTag);
      form.append('application_version', this.applicationVersion);
      if (this.environmentValue) form.append('environment', this.environmentValue);
      form.append('audience_roles', this.audienceRoles);

      const created = await this.sourcesService.upload(form);
      await this.router.navigate(['/sources', created.id]);
    } catch (e: any) {
      this.error.set(e?.error?.detail ?? 'Upload failed. Check the file type and size.');
    } finally {
      this.uploading.set(false);
    }
  }
}
