import { CommonModule } from '@angular/common';
import { Component, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApplicationsService, SourcesService, UsageService } from '../../core/api.services';
import { Application, SourceSummary, UsageSummary } from '../../core/models';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-dashboard', standalone: true, imports: [CommonModule, RouterLink],
  template: `
    <div class="space-y-7">
      <section class="relative isolate overflow-hidden rounded-[28px] border border-[#d9eae3] bg-[linear-gradient(115deg,#f1f8f4_0%,#fcfdfb_58%,#f6faf8_100%)] px-6 py-7 sm:px-9 sm:py-9">
        <div class="pointer-events-none absolute -right-10 -top-20 -z-10 h-72 w-72 rounded-full border border-[#e1eee8] sm:right-9 sm:top-1/2 sm:-translate-y-1/2" aria-hidden="true"></div>
        <div class="pointer-events-none absolute right-6 top-9 -z-10 hidden h-52 w-52 rounded-full border border-[#e8f1ec] sm:block" aria-hidden="true"></div>
        <div class="relative max-w-2xl">
          <p class="eyebrow mb-2">Workspace · {{ auth.activeMembership()?.organization_name || 'Your team' }}</p>
          <h1 class="text-3xl sm:text-[2.6rem] leading-tight font-semibold tracking-tight text-slate-950">Good to see you, {{ firstName() }}.</h1>
          <p class="mt-3 max-w-xl text-sm leading-6 text-slate-600">Get a quick answer from your team's approved training, then jump to the exact moment it came from.</p>
          <div class="mt-6 flex flex-wrap gap-3">
            <a routerLink="/assistant" class="btn-primary !rounded-full !px-5">Ask your team’s knowledge <svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4 10h11M10 5l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></a>
            <a routerLink="/sources" class="inline-flex items-center rounded-full border border-slate-200 bg-white/80 px-5 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:border-brand-300 hover:bg-white">Browse library</a>
            @if (auth.hasAtLeastRole('contributor')) { <a routerLink="/sources/upload" class="inline-flex items-center px-2 py-2.5 text-sm font-medium text-brand-800 hover:text-brand-950">Add a source <span aria-hidden="true" class="ml-1">↗</span></a> }
          </div>
        </div>
        <div class="absolute right-[5.7rem] top-1/2 hidden -translate-y-1/2 text-brand-700/70 sm:block" aria-hidden="true"><svg class="h-14 w-14" viewBox="0 0 56 56" fill="none"><path d="M28 5 33 23l18 5-18 5-5 18-5-18-18-5 18-5 5-18Z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><circle cx="46" cy="9" r="2" fill="currentColor"/></svg></div>
      </section>
      @if (error()) { <div class="notice flex justify-between gap-4" role="alert"><span>{{ error() }}</span><button class="font-semibold underline" (click)="load()">Retry</button></div> }
      @if (loading()) { <p class="text-sm text-slate-500" role="status">Loading your workspace…</p> }
      @else {
        <div class="flex flex-wrap items-center gap-x-8 gap-y-3 border-y border-slate-200/80 py-4">
          <div class="flex items-baseline gap-2"><span class="text-xl font-semibold tabular-nums text-slate-900">{{ sourceCount() }}</span><span class="text-xs text-slate-500">sources available</span></div>
          <div class="flex items-baseline gap-2"><span class="text-xl font-semibold tabular-nums text-slate-900">{{ applications().length }}</span><span class="text-xs text-slate-500">applications</span></div>
          <div class="flex items-baseline gap-2"><span class="text-xl font-semibold tabular-nums text-slate-900">{{ usage ? (usage.total_questions_asked | number) : '—' }}</span><span class="text-xs text-slate-500">questions · last 30 days</span></div>
          <div class="flex items-baseline gap-2"><span class="text-xl font-semibold tabular-nums text-slate-900">{{ usage ? (usage.total_processed_video_minutes | number: '1.0-0') : '—' }}<span class="ml-1 text-xs font-normal text-slate-500">min</span></span><span class="text-xs text-slate-500">processed · last 30 days</span></div>
        </div>
        <div class="grid xl:grid-cols-3 gap-6">
          <section class="xl:col-span-2 rounded-2xl border border-slate-200/80 bg-white p-5 sm:p-6">
            <div class="flex justify-between items-center gap-3 mb-4"><div><p class="eyebrow mb-1">Workspace library</p><h2 class="font-semibold text-lg">Recently added</h2></div><a routerLink="/sources" class="text-xs font-semibold text-brand-700 hover:text-brand-900">View library <span aria-hidden="true">→</span></a></div>
            @if (sources().length === 0) {
              <div class="py-10"><div class="flex h-11 w-11 items-center justify-center rounded-xl bg-[#eef7f3] text-brand-700" aria-hidden="true"><svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 9 6-9 6V6Z"/><rect x="3" y="3" width="18" height="18" rx="3"/></svg></div><h3 class="mt-4 text-sm font-semibold">Your library starts here</h3><p class="mt-2 text-sm text-slate-500 max-w-sm">{{ auth.hasAtLeastRole('contributor') ? 'Add a training video or guide so your team can search it and get useful answers.' : 'Approved team guides and videos will appear here.' }}</p>@if (auth.hasAtLeastRole('contributor')) { <a routerLink="/sources/upload" class="inline-flex mt-4 text-sm font-semibold text-brand-700 hover:text-brand-900">Add your first source <span aria-hidden="true" class="ml-1">→</span></a> }</div>
            } @else {
              <div class="divide-y divide-slate-100">
                @for (s of sources(); track s.id) {
                  <a [routerLink]="['/sources', s.id]" class="flex gap-3 items-center py-3.5 group"><span class="h-10 w-10 shrink-0 flex items-center justify-center rounded-xl bg-[#f1f7f4] text-brand-700" aria-hidden="true"><svg class="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">@if (s.source_type === 'video') { <path d="m9 6 9 6-9 6V6Z"/><rect x="3" y="3" width="18" height="18" rx="3"/> } @else { <path d="M6 3h8l4 4v14H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M14 3v5h5M8 12h8M8 16h8"/> }</svg></span><div class="min-w-0 flex-1"><p class="text-sm font-medium truncate group-hover:text-brand-700">{{ s.title }}</p><p class="text-xs text-slate-400 mt-1 capitalize">{{ s.source_type }} · {{ s.created_at | date: 'MMM d' }}</p></div><span class="badge capitalize" [ngClass]="statusClass(s.status)">{{ s.status.replace('_', ' ') }}</span></a>
                }
              </div>
            }
          </section>
          <section class="rounded-2xl border border-slate-200/80 bg-white p-5 sm:p-6"><p class="eyebrow mb-1">A quick start</p><h2 class="font-semibold text-lg">Make TrainU yours</h2>
            <ol class="mt-5 space-y-5">
              @if (auth.hasAtLeastRole('contributor')) {
                @if (auth.hasAtLeastRole('content_owner')) { <li class="flex gap-3"><span class="flex h-7 w-7 shrink-0 rounded-full bg-brand-50 text-brand-700 items-center justify-center text-xs">1</span><div><a routerLink="/applications" class="text-sm font-semibold hover:text-brand-700">Organize your applications →</a><p class="text-xs text-slate-500 mt-1 leading-relaxed">Group training by the tools and workflows your team uses.</p></div></li> }
                <li class="flex gap-3"><span class="flex h-7 w-7 shrink-0 rounded-full bg-brand-50 text-brand-700 items-center justify-center text-xs">2</span><div><a routerLink="/sources/upload" class="text-sm font-semibold hover:text-brand-700">{{ auth.hasAtLeastRole('content_owner') ? 'Upload, review, approve →' : 'Submit a source for review →' }}</a><p class="text-xs text-slate-500 mt-1 leading-relaxed">{{ auth.hasAtLeastRole('content_owner') ? 'Review the transcript before making a source searchable.' : 'Add a description and audience; a content owner will review your draft.' }}</p></div></li>
              }
              @if (auth.hasAtLeastRole('org_admin')) { <li class="flex gap-3"><span class="flex h-7 w-7 shrink-0 rounded-full bg-brand-50 text-brand-700 items-center justify-center text-xs">3</span><div><a routerLink="/admin/users" class="text-sm font-semibold hover:text-brand-700">Invite your team →</a><p class="text-xs text-slate-500 mt-1 leading-relaxed">Give each person the right access for their work.</p></div></li> }
              <li class="flex gap-3"><span class="flex h-7 w-7 shrink-0 rounded-full bg-brand-50 text-brand-700 items-center justify-center"><svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M10 2.5 12 8l5.5 2-5.5 2-2 5.5L8 12l-5.5-2L8 8l2-5.5Z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg></span><div><a routerLink="/help" class="text-sm font-semibold hover:text-brand-700">Explore the quick guide →</a><p class="text-xs text-slate-500 mt-1 leading-relaxed">Learn the basics, roles, and ways to use TrainU.</p></div></li>
            </ol>
          </section>
        </div>
      }
    </div>
  `,
})
export class DashboardComponent implements OnInit {
  loading = signal(true); error = signal<string | null>(null); usage: UsageSummary | null = null;
  sources = signal<SourceSummary[]>([]); sourceCount = signal(0); applications = signal<Application[]>([]);
  constructor(public auth: AuthService, private usageService: UsageService, private sourcesService: SourcesService, private applicationsService: ApplicationsService) {}
  firstName() { return this.auth.user()?.full_name?.split(' ')[0] || 'there'; }
  ngOnInit() { void this.load(); }
  async load() {
    this.loading.set(true); this.error.set(null);
    const [usage, sources, applications] = await Promise.allSettled([this.usageService.summary(), this.sourcesService.list(), this.applicationsService.list()]);
    if (usage.status === 'fulfilled') this.usage = usage.value;
    if (sources.status === 'fulfilled') { this.sourceCount.set(sources.value.length); this.sources.set(sources.value.slice(0, 5)); }
    if (applications.status === 'fulfilled') this.applications.set(applications.value);
    if ([usage, sources, applications].some(r => r.status === 'rejected')) this.error.set('Some workspace information could not be loaded. Try again to refresh it.');
    this.loading.set(false);
  }
  statusClass(status: string) { return ({ processing: 'bg-blue-50 text-blue-700', awaiting_review: 'bg-amber-50 text-amber-800', approved: 'bg-brand-50 text-brand-700', indexed: 'bg-brand-50 text-brand-700', failed: 'bg-red-50 text-red-700' } as Record<string, string>)[status] ?? 'bg-slate-100 text-slate-600'; }
}
