import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, ElementRef, Input, OnChanges, SimpleChanges, ViewChild, signal } from '@angular/core';

/** Plays a bounded transcript excerpt first and exposes the complete recording separately. */
@Component({
  selector: 'app-clip-player',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-3">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-sm font-semibold text-slate-800">Selected clip</p>
          <p class="text-xs text-slate-500">{{ formatTime(startSeconds) }}–{{ formatTime(endSeconds) }} · {{ formatTime(endSeconds - startSeconds) }} excerpt</p>
        </div>
        <span class="badge bg-brand-50 text-brand-700">Context only</span>
      </div>
      <video #clip class="w-full rounded-xl bg-slate-100 aspect-video" playsinline preload="metadata" [muted]="muted()" [src]="src" (loadedmetadata)="onMetadata()" (timeupdate)="onTimeUpdate()" (seeking)="onSeeking()" (play)="playing.set(true)" (pause)="playing.set(false)" (error)="error = 'This clip could not be played. Refresh the source and try again.'"></video>
      <div class="flex flex-wrap items-center gap-2">
        <button class="btn-secondary shrink-0" type="button" (click)="togglePlayback()" [attr.aria-label]="playing() ? 'Pause selected clip' : 'Play selected clip'">{{ playing() ? 'Pause' : 'Play clip' }}</button>
        <button class="btn-secondary shrink-0" type="button" (click)="toggleMute()" [attr.aria-pressed]="muted()" [attr.aria-label]="muted() ? 'Unmute selected clip' : 'Mute selected clip'">{{ muted() ? 'Unmute' : 'Mute' }}</button>
        <button class="btn-secondary shrink-0" type="button" (click)="stopClip()" aria-label="Stop selected clip">Stop</button>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-xs font-mono text-slate-600">{{ formatTime(clipTime()) }}</span>
        <input class="w-full accent-brand-600" type="range" [min]="startSeconds" [max]="effectiveEnd" step="0.1" [value]="clipTime()" aria-label="Seek within selected clip" (input)="seekClip($event)" />
        <span class="text-xs font-mono text-slate-600">{{ formatTime(effectiveEnd) }}</span>
      </div>
      @if (error) { <p class="text-xs text-red-700" role="alert">{{ error }}</p> }
      <p class="text-xs text-slate-500">Playback is limited to this transcript passage. The complete recording is available below.</p>
      <button class="text-sm font-medium text-brand-700 hover:text-brand-800" type="button" (click)="showFull = !showFull">{{ showFull ? 'Hide full video' : 'View full video ↓' }}</button>
      @if (showFull) {
        <div class="border-t border-slate-200 pt-3">
          <p class="text-sm font-semibold text-slate-800 mb-2">Full video</p>
          <video class="w-full rounded-xl bg-slate-100 aspect-video" controls playsinline preload="none" [src]="src"></video>
        </div>
      }
    </div>
  `,
})
export class ClipPlayerComponent implements OnChanges, AfterViewInit {
  @Input({ required: true }) src = '';
  @Input() startSeconds = 0;
  @Input() endSeconds = 0;
  @ViewChild('clip') clipRef?: ElementRef<HTMLVideoElement>;
  showFull = false;
  error = '';
  playing = signal(false);
  muted = signal(false);
  clipTime = signal(0);
  private boundedSeek = false;
  private viewReady = false;
  get effectiveEnd() {
    const duration = this.clipRef?.nativeElement.duration;
    return Math.min(this.endSeconds, Number.isFinite(duration) ? (duration ?? this.endSeconds) : this.endSeconds);
  }

  ngOnChanges(changes: SimpleChanges) {
    if (this.viewReady && (changes['startSeconds'] || changes['endSeconds'] || changes['src'])) this.resetClip();
  }

  ngAfterViewInit() {
    this.viewReady = true;
    this.resetClip();
  }

  private resetClip() {
    const video = this.clipRef?.nativeElement;
    if (!video) return;
    video.pause();
    this.playing.set(false);
    this.clipTime.set(this.startSeconds);
    this.error = '';
    this.showFull = false;
    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) this.onMetadata();
  }

  onMetadata() {
    const video = this.clipRef?.nativeElement;
    if (!video) return;
    const end = Math.min(this.endSeconds, Number.isFinite(video.duration) ? video.duration : this.endSeconds);
    if (end <= this.startSeconds) {
      this.error = 'This transcript passage has no playable duration.';
      return;
    }
    video.currentTime = this.startSeconds;
    this.clipTime.set(this.startSeconds);
  }

  onTimeUpdate() {
    const video = this.clipRef?.nativeElement;
    if (!video) return;
    const end = Math.min(this.endSeconds, Number.isFinite(video.duration) ? video.duration : this.endSeconds);
    this.clipTime.set(Math.min(video.currentTime, end));
    if (video.currentTime >= end) {
      video.pause();
      video.currentTime = Math.max(this.startSeconds, end - 0.04);
    }
  }

  togglePlayback() {
    const video = this.clipRef?.nativeElement;
    if (!video) return;
    if (video.paused) {
      if (video.currentTime < this.startSeconds || video.currentTime >= this.effectiveEnd - 0.04) video.currentTime = this.startSeconds;
      void video.play().catch(() => { this.error = 'Playback was blocked. Press Play clip again to start.'; });
    } else video.pause();
  }

  toggleMute() {
    const nextMuted = !this.muted();
    this.muted.set(nextMuted);
    if (this.clipRef?.nativeElement) this.clipRef.nativeElement.muted = nextMuted;
  }

  stopClip() {
    const video = this.clipRef?.nativeElement;
    if (!video) return;
    video.pause();
    video.currentTime = this.startSeconds;
    this.clipTime.set(this.startSeconds);
  }

  seekClip(event: Event) {
    const input = event.target as HTMLInputElement;
    const next = Math.min(this.effectiveEnd, Math.max(this.startSeconds, Number(input.value)));
    if (this.clipRef?.nativeElement) this.clipRef.nativeElement.currentTime = next;
    this.clipTime.set(next);
  }

  onSeeking() {
    const video = this.clipRef?.nativeElement;
    if (!video || this.boundedSeek) return;
    const end = Math.min(this.endSeconds, Number.isFinite(video.duration) ? video.duration : this.endSeconds);
    if (video.currentTime < this.startSeconds || video.currentTime >= end) {
      this.boundedSeek = true;
      video.currentTime = video.currentTime < this.startSeconds ? this.startSeconds : Math.max(this.startSeconds, end - 0.04);
      queueMicrotask(() => { this.boundedSeek = false; });
    }
  }

  formatTime(totalSeconds: number) {
    const seconds = Math.max(0, Math.round(totalSeconds || 0));
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
  }
}
