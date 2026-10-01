import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApplicationsService, SourcesService } from '../../core/api.services';
import { Application } from '../../core/models';
import { errorMessage } from '../../core/error-message';

@Component({
  selector: 'app-source-upload', standalone: true, imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="max-w-4xl space-y-6">
      <a routerLink="/sources" class="text-sm font-medium text-brand-700">← Knowledge library</a>
      <div><p class="eyebrow mb-2">Share what your team knows</p><h1 class="text-3xl font-semibold">Add knowledge</h1><p class="text-sm text-slate-500 mt-3">Upload training once. Help your team find the answer whenever they need it.</p></div>
      <form class="card p-5 sm:p-8 space-y-6" (ngSubmit)="submit()" #uploadForm="ngForm">
        <fieldset [disabled]="uploading()" class="space-y-6 min-w-0">
          <div class="rounded-2xl border-2 border-dashed border-brand-200 bg-brand-50/50 p-6 text-center">
            <span class="inline-flex h-12 w-12 rounded-xl bg-white text-2xl text-brand-700 items-center justify-center" aria-hidden="true">↑</span>
            <label class="block font-medium mt-3 mb-2" for="file">Choose a video or document</label>
            <input class="block max-w-full mx-auto text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-700 file:px-3 file:py-2 file:font-medium file:text-white" id="file" type="file" (change)="onFile($event)" required accept=".mp4,.mov,.m4v,.webm,.pdf,.docx,.md,.txt" aria-describedby="file-help" />
            <p id="file-help" class="mt-3 text-xs text-slate-500">MP4, MOV, M4V, WebM · up to 1 GB. PDF, DOCX, Markdown, TXT · up to 50 MB.</p>
            @if (file) { <p class="text-sm text-brand-800 mt-3 font-medium break-all">{{ file.name }} · {{ file.size / 1048576 | number: '1.1-1' }} MB</p> }
          </div>
          <div><label class="label" for="title">Title <span class="text-red-600">*</span></label><input class="input" id="title" name="title" required maxlength="300" [(ngModel)]="title" placeholder="e.g. Getting started with the approval workflow" /></div>
          <div><label class="label" for="description">Description</label><textarea class="input" id="description" name="description" rows="2" maxlength="5000" [(ngModel)]="description" placeholder="What will your team learn from this source?"></textarea></div>
          <div class="grid sm:grid-cols-2 gap-4">
            <div><label class="label" for="application">Application</label><select class="input" id="application" name="application" [(ngModel)]="applicationId"><option [ngValue]="null">General knowledge</option>@for (a of applications(); track a.id) { <option [ngValue]="a.id">{{ a.name }}</option> }</select></div>
            <div><label class="label" for="feature">Feature tag</label><input class="input" id="feature" name="feature" maxlength="200" [(ngModel)]="featureTag" placeholder="e.g. onboarding" /></div>
            <div><label class="label" for="version">Application version</label><input class="input" id="version" name="version" maxlength="100" [(ngModel)]="applicationVersion" placeholder="e.g. 3.4.1" /></div>
            <div><label class="label" for="env">Environment</label><select class="input" id="env" name="env" [(ngModel)]="environmentValue"><option [ngValue]="null">Not specified</option><option value="development">Development</option><option value="uat">UAT</option><option value="production">Production</option></select></div>
          </div>
          <div><p class="label">Audience</p><p class="text-xs text-slate-500 mb-3">Leave all unchecked for everyone in this workspace. Select roles to restrict who can learn from this source.</p><div class="flex flex-wrap gap-3">@for (role of audienceOptions; track role.value) { <label class="flex items-center gap-2 text-sm rounded-xl border border-slate-200 px-3 py-2"><input type="checkbox" [name]="role.value" [checked]="audience.has(role.value)" (change)="toggleAudience(role.value)" class="accent-emerald-700" />{{ role.label }}</label> }</div></div>
        </fieldset>
        @if (error()) { <p class="rounded-xl bg-red-50 p-4 text-sm text-red-700" role="alert">{{ error() }}</p> }
        @if (uploading()) {
          <div role="status" aria-live="polite"><div class="flex justify-between text-sm text-brand-800 mb-2"><span>{{ progress() === 100 ? 'Upload received. Preparing your source…' : 'Uploading your source…' }}</span>@if (progress() !== null) { <span>{{ progress() }}%</span> }</div><div class="h-2 rounded-full bg-brand-50 overflow-hidden" role="progressbar" aria-label="File upload" [attr.aria-valuenow]="progress()" aria-valuemin="0" aria-valuemax="100"><div class="h-full bg-brand-600 rounded-full transition-all" [class.animate-pulse]="progress() === null" [style.width.%]="progress() ?? 30"></div></div><p class="text-xs text-slate-500 mt-2">Keep this page open until the upload finishes. Processing continues in the background.</p></div>
        }
        <div class="border-t border-slate-100 pt-5 flex flex-wrap gap-4 items-center justify-between"><p class="text-xs text-slate-500 max-w-sm">Your source becomes searchable after processing and owner approval. Only upload content you have permission to use.</p><button type="submit" class="btn-primary" [disabled]="uploading() || !file || uploadForm.invalid || !title.trim()">{{ uploading() ? 'Uploading…' : 'Upload & process →' }}</button></div>
      </form>
    </div>
  `,
})
export class SourceUploadComponent implements OnInit {
  applications = signal<Application[]>([]); file: File | null = null; title = ''; description = '';
  applicationId: string | null = null; featureTag = ''; applicationVersion = ''; environmentValue: string | null = null;
  audience = new Set<string>(); uploading = signal(false); progress = signal<number | null>(null); error = signal<string | null>(null);
  audienceOptions = [{ value: 'viewer', label: 'Viewers' }, { value: 'contributor', label: 'Contributors' }, { value: 'content_owner', label: 'Content owners' }, { value: 'org_admin', label: 'Admins' }];
  constructor(private applicationsService: ApplicationsService, private sourcesService: SourcesService, private router: Router, private route: ActivatedRoute) {}
  async ngOnInit() {
    try {
      this.applications.set(await this.applicationsService.list());
      const qp = this.route.snapshot.queryParamMap.get('applicationId');
      if (qp && this.applications().some(a => a.id === qp)) this.applicationId = qp;
    } catch (e) { this.error.set(errorMessage(e, 'Applications could not be loaded. Refresh to choose an application.')); }
  }
  toggleAudience(role: string) { if (this.audience.has(role)) this.audience.delete(role); else this.audience.add(role); }
  onFile(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null; this.error.set(null); this.file = null;
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    const video = ['mp4', 'mov', 'm4v', 'webm'].includes(ext);
    const allowed = video || ['pdf', 'docx', 'md', 'txt'].includes(ext);
    if (!allowed) this.error.set('Choose a supported video or document format.');
    else if (!file.size) this.error.set('This file is empty. Choose a file with content.');
    else if (file.size > (video ? 1024 : 50) * 1048576) this.error.set(`This file is too large. The limit is ${video ? '1 GB' : '50 MB'}.`);
    else { this.file = file; if (!this.title) this.title = file.name.replace(/\.[^.]+$/, ''); }
    if (!this.file) input.value = '';
  }
  async submit() {
    if (!this.file || this.uploading() || !this.title.trim()) return;
    this.error.set(null); this.progress.set(null); this.uploading.set(true);
    try {
      const form = new FormData(); form.append('file', this.file); form.append('title', this.title.trim()); form.append('description', this.description.trim());
      if (this.applicationId) form.append('application_id', this.applicationId);
      form.append('feature_tag', this.featureTag.trim()); form.append('application_version', this.applicationVersion.trim());
      if (this.environmentValue) form.append('environment', this.environmentValue);
      form.append('audience_roles', [...this.audience].join(','));
      const created = await this.sourcesService.upload(form, value => this.progress.set(value));
      await this.router.navigate(['/sources', created.id]);
    } catch (e) { this.error.set(errorMessage(e, 'Upload failed. Your file is still selected. Check your connection and try again.')); }
    finally { this.uploading.set(false); }
  }
}
