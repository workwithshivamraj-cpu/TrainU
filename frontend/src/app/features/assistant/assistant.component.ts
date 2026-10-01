import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, DestroyRef, ElementRef, OnDestroy, OnInit, signal, ViewChild } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { combineLatest } from 'rxjs';
import { PENDING_QUESTION_KEY } from '../../core/external-question';
import { errorMessage } from '../../core/error-message';
import { FormsModule } from '@angular/forms';
import { ApplicationsService, AssistantService, SourcesService } from '../../core/api.services';
import { Application, AskResponse, ChatTurn, Citation } from '../../core/models';
import { ClipPlayerComponent } from '../../shared/clip-player.component';
import { animate, stagger } from 'motion';

declare global {
  interface Window {
    webkitSpeechRecognition?: any;
    SpeechRecognition?: any;
  }
}

@Component({
  selector: 'app-assistant',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, ClipPlayerComponent],
  template: `
    <div #assistantRoot class="assistant-root min-h-[70vh] flex flex-col">
      <div class="mb-6 flex flex-wrap items-center justify-between gap-4" data-motion="enter">
        <div>
          <p class="eyebrow mb-1">Your team's knowledge, in conversation</p><h1 class="text-[2rem] leading-tight font-semibold tracking-tight text-slate-950">Ask TrainU</h1>
          <p class="text-sm text-slate-500 mt-1">Ask naturally. Check every answer against its source.</p>
        </div>
        <div class="flex items-center gap-2 rounded-full border border-slate-200 bg-white pl-3 pr-1.5 py-1.5 shadow-sm">
          <label class="text-[11px] uppercase tracking-wide text-slate-500" for="app-filter">Focus</label>
          <select id="app-filter" class="max-w-48 border-0 bg-transparent py-1 pl-1 pr-7 text-sm font-medium text-slate-800 focus:ring-0" [(ngModel)]="selectedApplicationId" (ngModelChange)="conversationId = null">
            <option [ngValue]="null">All applications</option>
            @for (a of applications(); track a.id) {
              <option [ngValue]="a.id">{{ a.name }}</option>
            }
          </select>
        </div>
      </div>

      @if (externalDraft()) { <div class="rounded-xl bg-brand-50 text-brand-800 p-4 text-sm mb-4" role="status">Your selected text is ready below. Review it, then press Ask to send it to TrainU.</div> }
      @if (error()) { <p class="rounded-xl bg-red-50 text-red-700 p-3 text-sm mb-4" role="alert">{{ error() }}</p> }
      <div [ngClass]="activeVideo() ? 'grid grid-cols-1 lg:grid-cols-5 gap-4 flex-1 min-h-0' : 'flex flex-1 min-h-0'">
        <!-- Conversation column -->
        <div [ngClass]="activeVideo() ? 'lg:col-span-3 flex flex-col min-h-0' : 'flex flex-col min-h-0 w-full max-w-5xl mx-auto'">
          <div class="assistant-conversation flex-1 min-h-[330px] max-h-[68vh] overflow-y-auto px-1 sm:px-3 py-2 space-y-5" #scrollRegion>
            @if (turns().length === 0) {
              <div class="assistant-empty h-full min-h-[330px] flex flex-col items-center justify-center text-center py-10 sm:py-14 px-4" data-motion="enter">
                <div class="relative mb-6 flex h-[68px] w-[68px] items-center justify-center rounded-[22px] bg-[#e9f6f1] text-brand-700">
                  <span class="absolute inset-0 rounded-[22px] border border-brand-100"></span>
                  <svg class="h-8 w-8" viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M16 3.5 19 13l9.5 3-9.5 3-3 9.5L13 19l-9.5-3 9.5-3 3-9.5Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><circle cx="25.5" cy="7" r="1.4" fill="currentColor"/></svg>
                </div>
                <p class="text-[11px] font-semibold uppercase tracking-[.16em] text-brand-700">Ask what you need</p>
                <h2 class="mt-2 text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">Get unstuck, quickly.</h2>
                <p class="mt-2 max-w-md text-sm leading-6 text-slate-500">Find a clear answer in your team's approved training, with the exact moment to watch.</p>
                <div class="mt-7 grid w-full max-w-[700px] grid-cols-1 sm:grid-cols-3 gap-3 text-left">
                  @for (ex of exampleQuestions; track ex) {
                    <button data-prompt class="quick-prompt group rounded-2xl border border-slate-200 bg-white px-4 py-4 text-left shadow-sm transition-colors hover:border-brand-300 hover:bg-[#fbfefd]" (click)="draftQuestion(ex)">
                      <span class="flex items-center justify-between gap-2"><span class="text-[11px] font-medium uppercase tracking-wide text-slate-400">{{ ex.kicker }}</span><svg class="h-4 w-4 text-slate-400 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M5 15 15 5M6 5h9v9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                      <span class="mt-3 block text-sm font-medium leading-5 text-slate-800">{{ ex.label }}</span>
                    </button>
                  }
                </div>
                <p class="mt-5 text-xs text-slate-400">Choose a prompt to draft it. You stay in control of when it sends.</p>
              </div>
            }

            @for (turn of turns(); track $index) {
              @if (turn.role === 'user') {
                <div class="flex justify-end">
                  <div class="bg-brand-700 text-white rounded-2xl rounded-br-none px-4 py-2 max-w-[85%] text-sm">
                    {{ turn.question }}
                  </div>
                </div>
              } @else {
                <div class="flex justify-start">
                  <div class="bg-slate-50 rounded-2xl rounded-bl-none px-4 py-3 max-w-[92%] w-full text-sm">
                    @if (turn.pending) {
                      <div class="flex items-center gap-2 text-slate-500">
                        <span class="animate-pulse">Thinking…</span>
                      </div>
                    } @else if (turn.response) {
                      <div class="flex items-start justify-between gap-2">
                        <p class="text-slate-800 whitespace-pre-line">{{ turn.response.answer }}</p>
                        <button
                          class="shrink-0 text-slate-400 hover:text-brand-600"
                          title="Listen to this answer"
                          aria-label="Listen to this answer"
                          (click)="speak(turn.response)"
                        >🔊</button>
                      </div>

                      @if (turn.response.steps.length) {
                        <ol class="mt-2 list-decimal list-inside space-y-1 text-slate-800">
                          @for (step of turn.response.steps; track $index) {
                            <li>{{ step }}</li>
                          }
                        </ol>
                      }

                      <div class="mt-2">
                        @if (!turn.response.citations.length && turn.response.inference_provider && turn.response.inference_provider !== 'none') {
                          <span class="badge bg-slate-100 text-slate-700">Conversation</span>
                        } @else {
                        <span class="badge" [ngClass]="confidenceClass(turn.response.confidence)">
                          Confidence: {{ turn.response.confidence }}
                        </span>
                        }
                        @if (turn.response.inference_provider === 'none') {
                          <span class="badge bg-slate-100 text-slate-600 ml-2">No model call · no approved evidence</span>
                        } @else if (turn.response.inference_provider === 'ollama') {
                          <span class="badge bg-emerald-50 text-emerald-800 ml-2">Local inference · {{ turn.response.inference_model }}</span>
                        } @else if (turn.response.inference_provider === 'mock') {
                          <span class="badge bg-amber-50 text-amber-800 ml-2">Demo response · no LLM</span>
                        } @else {
                          <span class="badge bg-blue-50 text-blue-800 ml-2">AI inference · {{ turn.response.inference_provider }}</span>
                        }
                      </div>

                      @if (turn.response.citations.length) {
                        <div class="mt-3 space-y-2">
                          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Sources</p>
                          @for (c of turn.response.citations; track c.chunk_id) {
                            <button
                              class="block w-full text-left rounded-md border border-slate-200 bg-white px-3 py-2 hover:border-brand-400 hover:bg-brand-50/40"
                              (click)="playCitation(c)"
                            >
                              <div class="flex items-center justify-between gap-2">
                                <span class="font-medium text-slate-800 text-sm">{{ c.source_title }}</span>
                                <span class="text-xs text-brand-700 font-mono">{{ formatTime(c.start_seconds) }}–{{ formatTime(c.end_seconds) }}</span>
                              </div>
                              @if (c.is_archived) {
                                <span class="badge bg-amber-50 text-amber-700 mt-1">Archived source</span>
                              }
                              <p class="text-xs text-slate-500 mt-1 line-clamp-2">{{ c.quoted_evidence }}</p>
                            </button>
                          }
                        </div>
                      }

                      @if (turn.response.related_clips.length) {
                        <div class="mt-3">
                          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Related clips</p>
                          <div class="flex flex-wrap gap-2 mt-1">
                            @for (r of turn.response.related_clips; track r.source_id + r.start_seconds) {
                              <button class="badge bg-slate-100 text-slate-600 hover:bg-slate-200" (click)="playRelated(r)">
                                {{ r.source_title }} · {{ formatTime(r.start_seconds) }}
                              </button>
                            }
                          </div>
                        </div>
                      }

                      @if (turn.response.follow_up_questions.length) {
                        <div class="mt-3">
                          <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">Follow-up questions</p>
                          <div class="flex flex-wrap gap-2 mt-1">
                            @for (f of turn.response.follow_up_questions; track f) {
                              <button class="badge bg-brand-50 text-brand-700 hover:bg-brand-100" [disabled]="asking()" (click)="questionText = f">{{ f }}</button>
                            }
                          </div>
                        </div>
                      }

                      @if (turn.response.message_id) { <div class="mt-3 flex items-center gap-2 border-t border-slate-200 pt-2">
                        <span class="text-xs text-slate-500">Was this helpful?</span>
                        <button
                          class="text-sm px-2 py-1 rounded"
                          [ngClass]="turn.response.__feedback === 'helpful' ? 'bg-emerald-100 text-emerald-700' : 'hover:bg-slate-200'"
                          (click)="submitFeedback(turn.response, 'helpful')"
                          aria-label="Mark as helpful"
                        >👍</button>
                        <button
                          class="text-sm px-2 py-1 rounded"
                          [ngClass]="turn.response.__feedback === 'not_helpful' ? 'bg-red-100 text-red-700' : 'hover:bg-slate-200'"
                          (click)="submitFeedback(turn.response, 'not_helpful')"
                          aria-label="Mark as not helpful"
                        >👎</button>
                      </div> }
                    }
                  </div>
                </div>
              }
            }
          </div>

          <form class="assistant-composer mt-3 flex items-center gap-2" (ngSubmit)="ask()">
            <button
              type="button"
              class="assistant-icon-btn shrink-0"
              [class.bg-red-50]="listening()"
              [attr.aria-pressed]="listening()"
              [disabled]="!voiceSupported"
              [title]="voiceSupported ? 'Ask by voice' : 'Voice input is not supported in this browser'"
              (click)="toggleListening()"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3m-4 0h8"/></svg>
              <span class="sr-only">{{ listening() ? 'Listening' : 'Ask by voice' }}</span>
            </button>
            <div class="assistant-input-wrap flex min-w-0 flex-1 items-center gap-3">
              <label class="sr-only" for="question">Ask a question</label>
              <input
              id="question"
              class="assistant-input"
              name="question"
              maxlength="2000"
              placeholder="Ask a question or describe what you're trying to do…"
              [(ngModel)]="questionText"
              [disabled]="asking()"
              />
              <button type="submit" class="assistant-send shrink-0" [disabled]="asking() || !questionText.trim()">
              <span>{{ asking() ? 'Thinking' : 'Ask' }}</span><svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4 10h11M10 5l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </button>
            </div>
          </form><p class="text-center text-[11px] text-slate-400 mt-2">AI can make mistakes. Verify important steps with the cited source. {{ voiceSupported ? 'Voice input is ready.' : '' }}</p>
        </div>

        <!-- Video column -->
        @if (activeVideo()) { <div class="assistant-citation-panel lg:col-span-2 min-h-0 self-stretch" data-motion="enter">
          <div class="rounded-2xl border border-slate-200 bg-white p-4 h-full flex flex-col shadow-sm">
            <div class="flex items-center justify-between gap-2 mb-3"><h2 class="text-sm font-semibold text-slate-800">Cited moment</h2><button type="button" class="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Close cited moment" (click)="closeCitation()"><svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg></button></div>@if (playbackError()) { <p class="text-sm text-red-700 mb-3" role="alert">{{ playbackError() }}</p> }
            @if (activeVideo()) {
              @if (activeVideo()?.isVideo) {
                <app-clip-player [src]="activeVideo()?.url ?? ''" [startSeconds]="activeVideo()?.time ?? 0" [endSeconds]="activeVideo()?.end ?? 0"></app-clip-player>
              } @else { <div class="rounded-xl bg-brand-50 p-6 text-sm text-brand-800">This reference comes from a document. Open the source to read its extracted text.</div> }
              <a [routerLink]="['/sources', activeVideo()?.sourceId]" class="inline-block text-sm font-medium text-brand-700 mt-3">Open source details →</a>
              <p class="mt-2 text-sm font-medium text-slate-800">{{ activeVideo()?.title }}</p>
              @if (activeVideo()?.isVideo) { <p class="text-xs text-slate-500">Transcript context: {{ activeVideo()?.evidence || 'Related source passage' }}</p> }
            } @else {
              <div class="flex-1 flex flex-col items-center justify-center text-center text-slate-400 border border-dashed border-slate-300 rounded-md p-8">
                <p class="text-sm">Click a citation to play the exact video segment here.</p>
              </div>
            }
          </div>
        </div> }
      </div>
    </div>
  `,
  styles: [`
    .assistant-composer { padding: .45rem; border: 1px solid #dce5e2; border-radius: 1.35rem; background: white; box-shadow: 0 12px 32px -28px rgb(16 55 46 / 30%); transition: border-color .18s ease, box-shadow .18s ease; }
    .assistant-composer:focus-within { border-color: #70b5a2; box-shadow: 0 0 0 4px rgb(16 150 116 / 8%), 0 12px 32px -28px rgb(16 55 46 / 30%); }
    .assistant-icon-btn { display: inline-flex; height: 2.9rem; width: 2.9rem; align-items: center; justify-content: center; border-radius: 1rem; border: 1px solid transparent; color: #537067; transition: color .15s ease, background .15s ease; }
    .assistant-icon-btn:hover { background: #eff7f4; color: #08775d; }
    .assistant-icon-btn:disabled { opacity: .42; cursor: not-allowed; }
    .assistant-input-wrap { min-height: 2.9rem; padding-left: .3rem; }
    .assistant-input { min-width: 0; flex: 1; border: 0; background: transparent; padding: .65rem .3rem; color: #142b25; font-size: .93rem; outline: none; }
    .assistant-input::placeholder { color: #98a8a2; }
    .assistant-input:focus { box-shadow: none; }
    .assistant-send { display: inline-flex; min-width: 5.8rem; height: 2.8rem; align-items: center; justify-content: center; gap: .55rem; border-radius: .95rem; background: #08775d; color: white; padding: 0 .9rem; font-size: .86rem; font-weight: 600; transition: background .15s ease, transform .15s ease; }
    .assistant-send:hover:not(:disabled) { background: #06654f; transform: translateY(-1px); }
    .assistant-send:disabled { background: #b7cfc7; cursor: not-allowed; }
    .assistant-conversation { scrollbar-color: #d5e2dd transparent; scrollbar-width: thin; }
    @media (max-width: 640px) { .assistant-send { min-width: 2.8rem; width: 2.8rem; padding: 0; } .assistant-send span { display: none; } .assistant-composer { gap: .2rem; } }
  `],
})
export class AssistantComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('assistantRoot') private assistantRoot?: ElementRef<HTMLElement>;
  applications = signal<Application[]>([]);
  selectedApplicationId: string | null = null;
  questionText = '';
  externalDraft = signal(false);
  error = signal<string | null>(null);
  playbackError = signal<string | null>(null);
  asking = signal(false);
  listening = signal(false);
  turns = signal<ChatTurn[]>([]);
  conversationId: string | null = null;
  activeVideo = signal<{ sourceId: string; title: string; url: string; time: number; end: number; evidence: string; isVideo: boolean } | null>(null);

  exampleQuestions = [
    { kicker: 'Find a process', label: 'How do I create a new client account?', question: 'How do I create a new client account?' },
    { kicker: 'Show me the moment', label: 'Where do I update an account status?', question: 'Where do I update the status of a client account?' },
    { kicker: 'Check a policy', label: 'Who can approve a status change?', question: 'Which role can approve a client account status change?' },
  ];

  private recognition: any = null;
  private motionCleanups: Array<() => void> = [];
  private promptAnimations = new Map<HTMLElement, { stop: () => void }>();
  voiceSupported = false;

  constructor(
    private applicationsService: ApplicationsService,
    private assistantService: AssistantService,
    private sourcesService: SourcesService,
    private route: ActivatedRoute, private router: Router, private destroyRef: DestroyRef
  ) {}

  ngAfterViewInit() {
    const root = this.assistantRoot?.nativeElement;
    if (!root || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const entrances = root.querySelectorAll<HTMLElement>('[data-motion="enter"]');
    if (entrances.length) {
      const reveal = animate(entrances, { opacity: [0, 1], y: [12, 0] }, { duration: 0.38, delay: stagger(0.07), ease: 'easeOut' });
      this.motionCleanups.push(() => reveal.stop());
    }
    root.querySelectorAll<HTMLElement>('[data-prompt]').forEach((prompt) => {
      const enter = () => { this.promptAnimations.get(prompt)?.stop(); this.promptAnimations.set(prompt, animate(prompt, { y: -2, scale: 1.012 }, { duration: 0.16, ease: 'easeOut' })); };
      const leave = () => { this.promptAnimations.get(prompt)?.stop(); this.promptAnimations.set(prompt, animate(prompt, { y: 0, scale: 1 }, { duration: 0.2, ease: 'easeOut' })); };
      prompt.addEventListener('pointerenter', enter);
      prompt.addEventListener('pointerleave', leave);
      this.motionCleanups.push(() => { prompt.removeEventListener('pointerenter', enter); prompt.removeEventListener('pointerleave', leave); });
    });
  }

  draftQuestion(prompt: { question: string }) {
    this.questionText = prompt.question;
    this.externalDraft.set(false);
    requestAnimationFrame(() => document.getElementById('question')?.focus());
  }

  closeCitation() { this.activeVideo.set(null); this.playbackError.set(null); }

  async ngOnInit() {
    const pending = sessionStorage.getItem(PENDING_QUESTION_KEY);
    if (pending) { this.questionText = pending.slice(0, 2000); this.externalDraft.set(true); sessionStorage.removeItem(PENDING_QUESTION_KEY); }
    combineLatest([this.route.queryParamMap, this.route.fragment]).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(([params, fragment]) => {
      const selected = new URLSearchParams(fragment ?? '').get('q') ?? params.get('q');
      if (selected !== null) {
        this.questionText = selected.slice(0, 2000); this.externalDraft.set(true);
        const queryParams = { ...this.route.snapshot.queryParams }; delete queryParams['q'];
        void this.router.navigate([], { relativeTo: this.route, queryParams, fragment: undefined, replaceUrl: true });
      }
    });
    try { this.applications.set(await this.applicationsService.list()); }
    catch (e) { this.error.set(errorMessage(e, 'Application filters could not be loaded. You can still try a question.')); }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.voiceSupported = true;
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.lang = 'en-US';
      this.recognition.onresult = (event: any) => {
        this.questionText = event.results[0][0].transcript;
      };
      this.recognition.onend = () => this.listening.set(false);
      this.recognition.onerror = () => this.listening.set(false);
    }
  }

  toggleListening() {
    if (!this.recognition) return;
    if (this.listening()) {
      this.recognition.stop();
      this.listening.set(false);
    } else {
      try { this.recognition.start(); this.listening.set(true); }
      catch { this.error.set('Microphone access is unavailable. You can type your question instead.'); }
    }
  }

  async ask(preset?: string) {
    const question = (preset ?? this.questionText).trim();
    if (!question || this.asking()) return;
    if (question.length > 2000) { this.error.set("Keep your question under 2,000 characters."); return; }
    this.error.set(null); this.externalDraft.set(false);
    this.questionText = '';
    this.turns.update((t) => [...t, { role: 'user', question }, { role: 'assistant', pending: true }]);
    this.asking.set(true);
    try {
      const response = await this.assistantService.ask({
        question,
        application_id: this.selectedApplicationId,
        conversation_id: this.conversationId,
      });
      this.conversationId = response.conversation_id;
      this.turns.update((t) => {
        const copy = [...t];
        copy[copy.length - 1] = { role: 'assistant', response };
        return copy;
      });

    } catch (e) {
      this.questionText = question;
      this.turns.update((t) => {
        const copy = [...t];
        copy[copy.length - 1] = {
          role: 'assistant',
          response: {
            conversation_id: '',
            message_id: '',
            answer: errorMessage(e, 'Something went wrong reaching TrainU. Please try again.'),
            steps: [],
            confidence: 'none',
            citations: [],
            related_clips: [],
            follow_up_questions: [],
          },
        };
        return copy;
      });
    } finally {
      this.asking.set(false);
    }
  }

  async playCitation(c: Citation) {
    this.playbackError.set(null);
    try {
      const source = await this.sourcesService.get(c.source_id);
      if (source.source_type === 'video' && !source.playback_url) {
        this.playbackError.set('Playback is temporarily unavailable. Try the citation again in a moment.'); return;
      }
      this.activeVideo.set({ sourceId: c.source_id, title: c.source_title, url: source.playback_url ?? '', time: c.start_seconds, end: c.end_seconds, evidence: c.quoted_evidence, isVideo: source.source_type === 'video' });
    } catch (e) { this.playbackError.set(errorMessage(e, 'This source is not available for your account.')); }
  }
  ngOnDestroy() { this.recognition?.abort(); if ('speechSynthesis' in window) window.speechSynthesis.cancel(); this.motionCleanups.splice(0).forEach(cleanup => cleanup()); this.promptAnimations.forEach(animation => animation.stop()); this.promptAnimations.clear(); }

  playRelated(r: { source_id: string; source_title: string; start_seconds: number; end_seconds: number }) {
    this.playCitation({ ...r, chunk_id: '', quoted_evidence: '', confidence_score: 0, is_archived: false } as Citation);
  }

  speak(response: AskResponse) {
    if (!('speechSynthesis' in window)) return;
    const text = [response.answer, ...response.steps].join('. ');
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }

  async submitFeedback(response: AskResponse & { __feedback?: string }, rating: 'helpful' | 'not_helpful') {
    if (!response.message_id) return;
    try {
      await this.assistantService.feedback(response.message_id, rating);
      response.__feedback = rating;
    } catch (e) { this.error.set(errorMessage(e, 'Feedback could not be saved. Please try again.')); }
  }

  confidenceClass(confidence: string): string {
    return (
      {
        high: 'bg-emerald-50 text-emerald-700',
        medium: 'bg-amber-50 text-amber-700',
        low: 'bg-orange-50 text-orange-700',
        none: 'bg-slate-100 text-slate-500',
      } as Record<string, string>
    )[confidence];
  }

  formatTime(totalSeconds: number): string {
    const s = Math.max(0, Math.round(totalSeconds));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${r.toString().padStart(2, '0')}`;
  }
}
