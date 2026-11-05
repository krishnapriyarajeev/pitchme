import { readMetrics } from '@/lib/api';
import { isSettling, rehearsalState, sessionMeta, STATE_TEXT } from '@/lib/sessions';

describe('rehearsalState', () => {
  it.each([
    [{ status: 'waiting', analysis_status: 'not_started' }, 'waiting'],
    [{ status: 'active', analysis_status: 'not_started' }, 'live'],
    [{ status: 'failed', analysis_status: 'not_started', end_reason: 'no_show' }, 'no_show'],
    [{ status: 'failed', analysis_status: 'not_started', end_reason: 'lost' }, 'call_failed'],
    [{ status: 'complete', analysis_status: 'not_started' }, 'ready'],
    [{ status: 'complete', analysis_status: 'queued' }, 'analysing'],
    [{ status: 'complete', analysis_status: 'running' }, 'analysing'],
    [{ status: 'complete', analysis_status: 'failed' }, 'analysis_failed'],
    [{ status: 'complete', analysis_status: 'complete' }, 'debrief'],
  ] as const)('%j is %s', (session, state) => {
    expect(rehearsalState(session)).toBe(state);
  });

  it('checks again only while something is still moving', () => {
    expect(['waiting', 'live', 'analysing'].every((s) => isSettling(s as never))).toBe(true);
    expect(isSettling('debrief')).toBe(false);
  });

  it('never calls a rehearsal bad or failed', () => {
    const words = Object.values(STATE_TEXT).join(' ').toLowerCase();
    expect(words).not.toMatch(/\b(bad|poor|failed|failure)\b/);
  });
});

it('describes a session in one line', () => {
  const now = new Date(2026, 10, 5, 12);
  expect(
    sessionMeta(
      {
        created_at: new Date(2026, 10, 5, 9).toISOString(),
        duration_seconds: 250.4,
        deal_stage: 'cold_call',
      },
      now,
    ),
  ).toBe('Today · 4 min 10 s · Cold call');
  expect(
    sessionMeta({ created_at: now.toISOString(), duration_seconds: null, deal_stage: 'demo' }, now),
  ).toBe('Today · Demo');
});

describe('readMetrics', () => {
  it('keeps the parts that are objects and drops the rest', () => {
    expect(readMetrics({ voice: { pitch: {} }, speech: 'oops', vision: null })).toEqual({
      voice: { pitch: {} },
      speech: undefined,
      vision: undefined,
    });
    expect(readMetrics(undefined)).toEqual({
      voice: undefined,
      speech: undefined,
      vision: undefined,
    });
  });
});
