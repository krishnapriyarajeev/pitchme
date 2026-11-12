import { bandFor, type Band } from '@/constants/bands';
import type { AnalysisResult, SessionSummary } from '@/lib/api';

export type ScoredSession = { id: string; at: string; score: number };

export type Progress = {
  /** Oldest first, for the trend line. */
  scored: ScoredSession[];
  latest: { score: number; band: Band } | null;
  /** Latest minus the one before it; null with fewer than two. */
  sinceLast: number | null;
  /** Latest minus the first; null with fewer than two. */
  sinceFirst: number | null;
  rehearsals: number;
};

/**
 * Progress from the user's reviewed rehearsals only. With no review yet,
 * there is nothing to show, and the screen says how to get one.
 */
export function progressFrom(sessions: SessionSummary[]): Progress {
  const scored = sessions
    .filter(
      (s) =>
        s.status === 'complete' && s.analysis_status === 'complete' && s.overall_score !== null,
    )
    .map((s) => ({ id: s.session_id, at: s.created_at, score: Math.round(s.overall_score!) }))
    .sort((a, b) => a.at.localeCompare(b.at));
  const last = scored.at(-1);
  const before = scored.at(-2);
  const first = scored[0];
  return {
    scored,
    latest: last ? { score: last.score, band: bandFor(last.score) } : null,
    sinceLast: last && before ? last.score - before.score : null,
    sinceFirst: last && first && scored.length > 1 ? last.score - first.score : null,
    rehearsals: sessions.length,
  };
}

export type DimensionAverage = { name: string; label: string; score: number; count: number };

/** Each dimension's average over the results that scored it. */
export function averageDimensions(
  results: Pick<AnalysisResult, 'dimensions'>[],
): DimensionAverage[] {
  const totals = new Map<string, DimensionAverage>();
  for (const result of results) {
    for (const dimension of result.dimensions) {
      if (dimension.score === null) continue;
      const total = totals.get(dimension.name) ?? {
        name: dimension.name,
        label: dimension.label,
        score: 0,
        count: 0,
      };
      total.score += dimension.score;
      total.count += 1;
      totals.set(dimension.name, total);
    }
  }
  return [...totals.values()].map((t) => ({ ...t, score: Math.round(t.score / t.count) }));
}

/** "+6 since last time", "Same as last time", "−4 since last time". */
export function changeText(change: number | null, since: string): string {
  if (change === null) return '';
  if (change === 0) return `Same as ${since}`;
  return `${change > 0 ? '+' : '−'}${Math.abs(change)} since ${since}`;
}
