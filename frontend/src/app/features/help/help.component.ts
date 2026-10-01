import { CommonModule } from '@angular/common';
import { Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-help', standalone: true, imports: [CommonModule, RouterLink],
  template: `
    <div class="max-w-6xl mx-auto space-y-8" [class.p-6]="!auth.isAuthenticated()">
      @if (!auth.isAuthenticated()) { <a routerLink="/login" class="inline-block text-brand-700 font-semibold">← TrainU · Sign in</a> }
      <header><p class="eyebrow mb-2">The TrainU handbook</p><h1 class="text-3xl font-semibold">A little guidance. A lot of clarity.</h1><p class="text-sm text-slate-500 mt-3">Getting started, working together, and running your workspace.</p></header>
      <nav class="flex flex-wrap gap-2" aria-label="Guide sections">
        @for (tab of tabs; track tab.id) { <button class="btn-secondary" [class.!bg-brand-50]="active() === tab.id" [class.!border-brand-300]="active() === tab.id" [attr.aria-pressed]="active() === tab.id" (click)="active.set(tab.id)">{{ tab.label }}</button> }
      </nav>
      @if (active() === 'start') {
        <div class="grid md:grid-cols-3 gap-5">
          @for (step of steps; track step.title; let i = $index) { <article class="card p-6"><span class="badge bg-brand-50 text-brand-700">0{{ i + 1 }}</span><h2 class="font-semibold text-lg mt-4">{{ step.title }}</h2><p class="text-sm text-slate-500 mt-2 leading-relaxed">{{ step.body }}</p><a [routerLink]="step.route" class="inline-block mt-5 text-sm font-semibold text-brand-700">{{ step.action }} →</a></article> }
        </div>
        <section class="card p-6"><h2 class="font-semibold text-lg">From upload to a useful answer</h2><ol class="mt-4 grid sm:grid-cols-4 gap-4 text-sm">@for (stage of stages; track stage.title) { <li class="rounded-xl bg-slate-50 p-4"><p class="font-semibold text-brand-800">{{ stage.title }}</p><p class="mt-2 text-slate-500 leading-relaxed">{{ stage.body }}</p></li> }</ol><p class="text-sm text-slate-500 mt-5">If a source fails, open its detail page for the reason. Correct the file or ask your administrator to check processing services before uploading it again.</p></section>
        <section class="card p-6"><h2 class="font-semibold text-lg">Ask a better question</h2><p class="text-sm text-slate-600 mt-3 leading-relaxed">Name the application, the task, and what you want to know. Select an application to narrow the search. Open the cited source to verify the answer, and use Helpful or Not helpful to leave feedback. Answers can be incomplete or incorrect; check the original source before important decisions.</p><p class="text-sm text-slate-500 mt-3">Voice input uses your browser's speech service when available. Review the text before pressing Ask.</p></section>
      }
      @if (active() === 'roles') {
        <section class="card p-6"><h2 class="font-semibold text-lg">The right access for each person</h2><p class="text-sm text-slate-500 mt-2">Your organization administrator assigns roles. Permissions are checked by the server for every request.</p><div class="overflow-x-auto mt-6"><table class="w-full text-sm text-left"><thead><tr class="border-b border-slate-200"><th class="py-3 pr-5">Role</th><th class="py-3 min-w-72">What they can do</th></tr></thead><tbody>@for (role of roles; track role.name) { <tr class="border-b border-slate-100 last:border-0"><th class="py-4 pr-5 font-medium whitespace-nowrap">{{ role.name }}</th><td class="py-4 text-slate-600 leading-relaxed">{{ role.body }}</td></tr> }</tbody></table></div></section>
        <div class="notice">Audience restrictions apply to source access and answers. Content owners and administrators manage workspace content. Review each source's audience before approval.</div>
        <section class="card p-6"><h2 class="font-semibold">Invite a teammate</h2><p class="text-sm text-slate-600 mt-3 leading-relaxed">Open People & roles, enter their email, select a role, and create an invitation. Share the invitation link through your team's trusted channel. They must use the invited email address. Invitation links expire and can be revoked by an administrator.</p></section>
      }
      @if (active() === 'extension') {
        <section class="rounded-3xl border border-brand-200 bg-brand-50 p-8"><p class="eyebrow">TrainU, where you work</p><h2 class="text-2xl font-semibold mt-3">A question is only a selection away.</h2><p class="text-sm text-brand-900/75 leading-relaxed mt-3 max-w-2xl">Select text on a web page, choose Ask TrainU from the context menu, and review the question in your workspace before you send it.</p></section>
        <div class="grid md:grid-cols-2 gap-6"><section class="card p-6"><h2 class="font-semibold text-lg">Install for a team pilot</h2><ol class="mt-4 list-decimal pl-5 space-y-3 text-sm text-slate-600"><li>Obtain the extension folder from your TrainU administrator.</li><li>Open Chrome or Edge's Extensions page, enable Developer mode, and choose Load unpacked.</li><li>Select the extension folder. Open its options and set your organization's TrainU address.</li><li>Use your HTTPS workspace URL in production; localhost HTTP is supported for development.</li></ol><p class="text-xs text-slate-500 mt-5">The packaged extension is for controlled pilots. Public store distribution requires a separate review and publishing process.</p></section><section class="card p-6"><h2 class="font-semibold text-lg">You stay in control</h2><ul class="mt-4 space-y-3 text-sm text-slate-600 list-disc pl-5"><li>The extension opens TrainU with the text you selected, up to 2,000 characters.</li><li>It does not read whole pages or upload video files.</li><li>Your selection stays in the draft until you press Ask.</li><li>Sign in with your usual account. Your workspace and role still apply.</li><li>Review selections for confidential content before submitting.</li></ul></section></div>
      }
      @if (active() === 'trust') {
        <div class="grid md:grid-cols-2 gap-6">
        <section class="card p-6"><h2 class="font-semibold text-lg">Data & privacy</h2><p class="text-sm text-slate-600 mt-3 leading-relaxed">TrainU stores account details, workspace memberships, uploaded sources, extracted text, questions, answers, and feedback. Your workspace administrator can explain the AI processing providers, hosting region, retention policy and available data requests for this installation.</p><p class="text-sm text-slate-600 mt-3 leading-relaxed">Only upload content your organization is authorized to process. Source access follows your organization role and each source's audience.</p></section>
        <section class="card p-6"><h2 class="font-semibold text-lg">Workspace operations</h2><p class="text-sm text-slate-600 mt-3 leading-relaxed">Your administrator manages invitations, content review, usage and source removal. Ask them about this workspace's support, backup and retention arrangements.</p><p class="text-sm text-slate-600 mt-3 leading-relaxed">Available features depend on how this TrainU workspace is configured.</p></section>
        </div>
      }
      @if (active() === 'documents') {
        <p class="text-sm text-slate-500">These customer guides explain the product and the sample workspace.</p>
        <div class="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">@for (doc of documents; track doc.file) { <a [href]="'/docs/' + doc.file + '.md'" target="_blank" rel="noopener" class="card p-5 hover:border-brand-300 transition-colors"><span class="text-brand-700 text-xl" aria-hidden="true">↗</span><h2 class="font-semibold mt-3">{{ doc.title }}</h2><p class="text-sm text-slate-500 leading-relaxed mt-2">{{ doc.body }}</p></a> }</div>
      }
      <footer class="border-t border-slate-200 pt-5 text-xs text-slate-500">Need help with access or a failed source? Contact your workspace administrator. Include the source title and what happened.</footer>
    </div>
  `,
})
export class HelpComponent {
  active = signal('start');
  constructor(public auth: AuthService) {}
  tabs = [{ id: 'start', label: 'Get started' }, { id: 'roles', label: 'People & permissions' }, { id: 'extension', label: 'Browser extension' }, { id: 'trust', label: 'Privacy & operations' }, { id: 'documents', label: 'All documents' }];
  steps = [
    { title: 'Bring knowledge together', body: 'Content owners add videos or documents and organize them by application. Give each source a clear title and audience.', route: '/sources', action: 'Open the library' },
    { title: 'Ask. Learn. Verify.', body: 'Ask a work question in your own words. Follow references back to the approved training and exact video moment.', route: '/assistant', action: 'Ask a question' },
    { title: 'Keep knowledge useful', body: 'Share feedback on answers. Owners can review transcripts and archive training that no longer matches the way your team works.', route: '/feedback', action: 'View feedback' },
  ];
  stages = [{ title: '1. Upload', body: 'A content owner adds a supported source.' }, { title: '2. Process', body: 'The worker extracts text and prepares search chunks.' }, { title: '3. Review', body: 'An owner checks the transcript, audience, and metadata.' }, { title: '4. Approve', body: 'Approved, indexed sources become available for answers.' }];
  roles = [
    { name: 'Viewer', body: 'Ask questions, open approved sources allowed for their audience, and provide answer feedback.' },
    { name: 'Contributor', body: 'Ask questions and submit video or document drafts for review. Content owners review transcripts and approve sources.' },
    { name: 'Content owner', body: 'Create applications; upload, review, edit, approve, and archive workspace sources.' },
    { name: 'Organization admin', body: 'All content owner permissions, plus manage people, invitations, workspace settings, audit logs, and source deletion.' },
    { name: 'Platform admin', body: 'Operator-level role. Organization membership and tenant access checks still apply. This role is not available through normal invitations.' },
  ];
  documents = [
    { file: 'product', title: 'Product & user guide', body: 'Use cases, user journeys, role behavior, and product scope.' },
    { file: 'demo-videos', title: 'Demo motion videos', body: 'The sample videos and the training topics they demonstrate.' },
  ];
}
