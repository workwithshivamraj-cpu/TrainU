import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnInit, ViewChild, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApplicationsService, AssistantService, SourcesService } from '../../core/api.services';
import { Application, AskResponse, ChatTurn, Citation } from '../../core/models';

declare global {
  interface Window {
    webkitSpeechRecognition?: any;
    SpeechRecognition?: any;
  }
}

@Component({
  selector: 'app-assistant',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="h-full flex flex-col">
      <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 class="text-xl font-semibold text-slate-900">Ask TrainU</h1>
          <p class="text-sm text-slate-500">Learn directly from your team's approved training knowledge.</p>
        </div>
        <div class="flex items-center gap-2">
          <label class="label mb-0 text-xs" for="app-filter">Application</label>
          <select id="app-filter" class="input py-1.5 text-sm w-56" [(ngModel)]="selectedApplicationId">
            <option [ngValue]="null">All applications</option>
            @for (a of applications(); track a.id) {
              <option [ngValue]="a.id">{{ a.name }}</option>
            }
          </select>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-5 gap-6 flex-1 min-h-0">
        <!-- Conversation column -->
        <div class="lg:col-span-3 flex flex-col min-h-0">
          <div class="card flex-1 overflow-y-auto p-4 space-y-5" #scrollRegion>
            @if (turns().length === 0) {
              <div class="h-full flex flex-col items-center justify-center text-center text-slate-400 py-16">
                <div class="text-4xl mb-3">✦</div>
                <p class="text-slate-600 font-medium">Ask TrainU. Learn directly from your team's approved training knowledge.</p>
                <div class="mt-4 flex flex-wrap gap-2 justify-center max-w-md">
                  @for (ex of exampleQuestions; track ex) {
                    <button class="badge bg-slate-100 text-slate-600 hover:bg-slate-200" (click)="ask(ex)">{{ ex }}</button>
                  }
                </div>
              </div>
            }

            @for (turn of turns(); track $index) {
              @if (turn.role === 'user') {
                <div class="flex justify-end">
                  <div class="bg-brand-600 text-white rounded-lg rounded-br-none px-4 py-2 max-w-[85%] text-sm">
                    {{ turn.question }}
                  </div>
                </div>
              } @else {
                <div class="flex justify-start">
                  <div class="bg-slate-100 rounded-lg rounded-bl-none px-4 py-3 max-w-[92%] w-full text-sm">
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
                        <span class="badge" [ngClass]="confidenceClass(turn.response.confidence)">
                          Confidence: {{ turn.response.confidence }}
                        </span>
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
                              <button class="badge bg-brand-50 text-brand-700 hover:bg-brand-100" (click)="ask(f)">{{ f }}</button>
                            }
                          </div>
                        </div>
                      }

                      <div class="mt-3 flex items-center gap-2 border-t border-slate-200 pt-2">
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
                      </div>
                    }
                  </div>
                </div>
              }
            }
          </div>

          <form class="mt-3 flex items-center gap-2" (ngSubmit)="ask()">
            <button
              type="button"
              class="btn-secondary shrink-0"
              [class.bg-red-50]="listening()"
              [attr.aria-pressed]="listening()"
              [disabled]="!voiceSupported"
              [title]="voiceSupported ? 'Ask by voice' : 'Voice input is not supported in this browser'"
              (click)="toggleListening()"
            >
              {{ listening() ? '● Listening' : '🎤' }}
            </button>
            <label class="sr-only" for="question">Ask a question</label>
            <input
              id="question"
              class="input"
              name="question"
              placeholder="e.g. How do I create a new client account?"
              [(ngModel)]="questionText"
              [disabled]="asking()"
            />
            <button type="submit" class="btn-primary shrink-0" [disabled]="asking() || !questionText.trim()">
              {{ asking() ? 'Asking…' : 'Ask' }}
            </button>
          </form>
        </div>

        <!-- Video column -->
        <div class="lg:col-span-2 min-h-0">
          <div class="card p-4 h-full flex flex-col">
            <h2 class="text-sm font-semibold text-slate-700 mb-2">Source clip</h2>
            @if (activeVideo()) {
              <video #videoPlayer class="w-full rounded-md bg-black aspect-video" controls></video>
              <p class="mt-2 text-sm font-medium text-slate-800">{{ activeVideo()?.title }}</p>
              <p class="text-xs text-slate-500">Playing at {{ formatTime(activeVideo()?.time ?? 0) }}</p>
            } @else {
              <div class="flex-1 flex flex-col items-center justify-center text-center text-slate-400 border border-dashed border-slate-300 rounded-md p-8">
                <p class="text-sm">Click a citation to play the exact video segment here.</p>
              </div>
            }
          </div>
        </div>
      </div>
    </div>
  `,
})
export class AssistantComponent implements OnInit {
  @ViewChild('videoPlayer') videoPlayerRef?: ElementRef<HTMLVideoElement>;

  applications = signal<Application[]>([]);
  selectedApplicationId: string | null = null;
  questionText = '';
  asking = signal(false);
  listening = signal(false);
  turns = signal<ChatTurn[]>([]);
  conversationId: string | null = null;
  activeVideo = signal<{ sourceId: string; title: string; url: string; time: number } | null>(null);

  exampleQuestions = [
    'How do I create a new client account?',
    'How do I update the status of a client account?',
    'Which role can approve a client account status change?',
    'How do I create a purchase order?',
  ];

  private recognition: any = null;
  voiceSupported = false;

  constructor(
    private applicationsService: ApplicationsService,
    private assistantService: AssistantService,
    private sourcesService: SourcesService
  ) {}

  async ngOnInit() {
    this.applications.set(await this.applicationsService.list().catch(() => []));
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
      this.recognition.start();
      this.listening.set(true);
    }
  }

  async ask(preset?: string) {
    const question = (preset ?? this.questionText).trim();
    if (!question) return;
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
      if (response.citations.length) {
        this.playCitation(response.citations[0]);
      }
    } catch (e) {
      this.turns.update((t) => {
        const copy = [...t];
        copy[copy.length - 1] = {
          role: 'assistant',
          response: {
            conversation_id: '',
            message_id: '',
            answer: 'Something went wrong reaching TrainU. Please try again.',
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
    try {
      const source = await this.sourcesService.get(c.source_id);
      this.activeVideo.set({
        sourceId: c.source_id,
        title: `${c.source_title} — ${this.formatTime(c.start_seconds)}–${this.formatTime(c.end_seconds)}`,
        url: source.playback_url ?? '',
        time: c.start_seconds,
      });
      queueMicrotask(() => {
        const el = this.videoPlayerRef?.nativeElement;
        if (el && source.playback_url) {
          el.src = source.playback_url;
          el.currentTime = c.start_seconds;
          el.play().catch(() => undefined);
        }
      });
    } catch {
      /* ignore playback errors in demo mode */
    }
  }

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
    try {
      await this.assistantService.feedback(response.message_id, rating);
      response.__feedback = rating;
    } catch {
      /* non-critical */
    }
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
