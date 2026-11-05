import type { SessionSummary } from '@/lib/api';
import { averageDimensions, changeText, progressFrom } from '@/lib/progress';

function session(id: string, day: number, score: number | null, extra = {}): SessionSummary {
  return {
    session_id: id,
    status: 'complete',
    prospect_name: 'Jo',
    company: 'Saber',
    deal_stage: 'discovery',
    duration_seconds: 60,
    created_at: new Date(2026, 10, day).toISOString(),
    analysis_status: score === null ? 'not_started' : 'complete',
    overall_score: score,
    ...extra,
  };
}

describe('progressFrom', () => {
  it('uses reviewed rehearsals only, oldest first', () => {
    const progress = progressFrom([
      session('c', 5, 82.4),
      session('x', 4, null),
      session('a', 1, 60),
      session('f', 3, null, { status: 'failed' }),
      session('b', 3, 74),
    ]);
    expect(progress.scored.map((s) => s.id)).toEqual(['a', 'b', 'c']);
    expect(progress.latest).toEqual({ score: 82, band: 'strong' });
    expect(progress.sinceLast).toBe(8);
    expect(progress.sinceFirst).toBe(22);
    expect(progress.rehearsals).toBe(5);
  });

  it('shows no score and no change with nothing reviewed', () => {
    expect(progressFrom([session('x', 1, null)])).toMatchObject({
      scored: [],
      latest: null,
      sinceLast: null,
      sinceFirst: null,
    });
    expect(progressFrom([session('a', 1, 70)]).sinceLast).toBeNull();
  });
});

it('averages each dimension over the reviews that scored it', () => {
  const dim = (name: string, score: number | null) => ({
    name,
    label: name,
    score,
    summary: '',
    skipped: null,
  });
  expect(
    averageDimensions([
      { dimensions: [dim('content', 80), dim('vision', null)] },
      { dimensions: [dim('content', 71), dim('vision', 90)] },
    ]),
  ).toEqual([
    { name: 'content', label: 'content', score: 76, count: 2 },
    { name: 'vision', label: 'vision', score: 90, count: 1 },
  ]);
});

it('says how the score moved', () => {
  expect(changeText(6, 'last time')).toBe('+6 since last time');
  expect(changeText(-4, 'last time')).toBe('−4 since last time');
  expect(changeText(0, 'last time')).toBe('Same as last time');
  expect(changeText(null, 'last time')).toBe('');
});
