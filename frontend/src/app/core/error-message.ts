/** Convert API/network validation failures into readable, bounded UI text. */
export function errorMessage(error: unknown, fallback: string): string {
  const e = error as { status?: number; error?: { detail?: unknown } };
  if (e?.status === 0) return 'Cannot reach TrainU. Check your connection and try again.';
  if (e?.status === 429) return 'Too many requests. Please wait a moment and try again.';
  if (e?.status === 413) return 'This file exceeds the upload limit. Choose a smaller file.';
  const detail = e?.error?.detail;
  if (typeof detail === 'string') return detail.slice(0, 400);
  if (Array.isArray(detail)) {
    return detail.map(v => typeof v?.msg === 'string' ? v.msg : '').filter(Boolean).slice(0, 3).join('. ') || fallback;
  }
  return fallback;
}
