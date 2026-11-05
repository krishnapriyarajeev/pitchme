import { DEAL_STAGES, labelFor } from '@/constants/deal';
import type { SessionSummary } from '@/lib/api';
import { dealTitle, formatDuration, formatRelativeDay } from '@/lib/format';

/**
 * One state for a rehearsal, from its call status and its analysis status.
 * Screens show this, so the two statuses are read the same way everywhere.
 */
export type RehearsalState =
  | 'waiting' // the room is open; the call has not started
  | 'live' // the call is running
  | 'no_show' // the user never joined
  | 'call_failed' // the call ended with an error, or the worker never reported
  | 'ready' // the call is over; no analysis yet
  | 'analysing'
  | 'analysis_failed'
  | 'debrief'; // the analysis is complete

type Statuses = Pick<SessionSummary, 'status' | 'analysis_status'> & {
  end_reason?: string | null;
};

export function rehearsalState(session: Statuses): RehearsalState {
  switch (session.status) {
    case 'waiting':
      return 'waiting';
    case 'active':
      return 'live';
    case 'failed':
      return session.end_reason === 'no_show' ? 'no_show' : 'call_failed';
    case 'complete':
      switch (session.analysis_status) {
        case 'queued':
        case 'running':
          return 'analysing';
        case 'failed':
          return 'analysis_failed';
        case 'complete':
          return 'debrief';
        default:
          return 'ready';
      }
  }
}

/** A few words for a list row. */
export const STATE_LABEL: Record<RehearsalState, string> = {
  waiting: 'Starting',
  live: 'In the call',
  no_show: 'Not joined',
  call_failed: 'Call stopped',
  ready: 'Ready to review',
  analysing: 'Reviewing',
  analysis_failed: 'Review stopped',
  debrief: 'Debrief ready',
};

/** One sentence for the session hub. Each one says what to do next. */
export const STATE_TEXT: Record<RehearsalState, string> = {
  waiting: 'The call has not started yet.',
  live: 'The call is still running.',
  no_show: 'You did not join this call, so there is nothing to review. Start a new rehearsal.',
  call_failed:
    'The call stopped before it finished, so there is nothing to review. Start a new rehearsal.',
  ready: 'The call is over. Choose a review to get your debrief.',
  analysing: 'PitchMe is reviewing your call.',
  analysis_failed: 'The review stopped early. Your recording is safe; run the review again.',
  debrief: 'Your debrief is ready.',
};

/** States that are still moving and need the screen to check again. */
export function isSettling(state: RehearsalState): boolean {
  return state === 'waiting' || state === 'live' || state === 'analysing';
}

export function sessionTitle(session: Pick<SessionSummary, 'prospect_name' | 'company'>): string {
  return dealTitle(session.prospect_name, session.company);
}

/** "Today · 4 min 10 s · Discovery". */
export function sessionMeta(
  session: Pick<SessionSummary, 'created_at' | 'duration_seconds' | 'deal_stage'>,
  now = new Date(),
): string {
  return [
    formatRelativeDay(session.created_at, now),
    session.duration_seconds ? formatDuration(session.duration_seconds) : null,
    labelFor(DEAL_STAGES, session.deal_stage),
  ]
    .filter(Boolean)
    .join(' · ');
}
