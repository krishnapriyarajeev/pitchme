/** Formats in one place, so a duration reads the same on every screen. */

/** "3 min 04 s". The API sends fractional seconds; they are rounded. */
export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return m === 0 ? `${s} s` : `${m} min ${String(s).padStart(2, '0')} s`;
}

/** "0:42" or "12:05", for a running timer. */
export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}

/** A moment in the recording, from milliseconds: "1:05". */
export function formatMoment(ms: number): string {
  return formatClock(ms / 1000);
}

function startOfDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

/**
 * "Today", "Yesterday", a weekday within the last week, then a date. A date
 * from another year shows the year.
 */
export function formatRelativeDay(iso: string, now = new Date()): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return '';
  const days = Math.round((startOfDay(now) - startOfDay(then)) / 86_400_000);
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days > 1 && days < 7) return then.toLocaleDateString('en', { weekday: 'long' });
  return formatShortDate(iso, now);
}

/** "5 Nov", or "5 Nov 2025" for another year. */
export function formatShortDate(iso: string, now = new Date()): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return '';
  return then.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    ...(then.getFullYear() === now.getFullYear() ? {} : { year: 'numeric' }),
  });
}

/** "2.4 MB": one decimal at most. */
export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes || bytes < 0) return '';
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${Math.round(kb)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

/** "PDF" from "playbook.pdf"; "File" when there is no extension. */
export function fileKind(name: string): string {
  const dot = name.lastIndexOf('.');
  return dot > 0 && dot < name.length - 1 ? name.slice(dot + 1).toUpperCase() : 'File';
}

/** "Jo Bennett · Saber Industries". */
export function dealTitle(prospect: string, company: string): string {
  return [prospect.trim(), company.trim()].filter(Boolean).join(' · ');
}
