import { request } from '@/lib/api/client';
import type {
  Analysis,
  AnalysisMode,
  AnalysisStatus,
  CallRoom,
  NewSession,
  SessionDetail,
  SessionSummary,
} from '@/lib/api/types';

/** Opens a call with the AI buyer. Join the room with the returned token. */
export function createSession(deal: NewSession): Promise<CallRoom> {
  return request<CallRoom>('/api/sessions', { method: 'POST', body: deal });
}

/** Newest first. */
export function listSessions(limit = 20, offset = 0): Promise<SessionSummary[]> {
  return request<SessionSummary[]>(`/api/sessions?limit=${limit}&offset=${offset}`);
}

export function getSession(id: string): Promise<SessionDetail> {
  return request<SessionDetail>(`/api/sessions/${encodeURIComponent(id)}`);
}

/**
 * Queues the analysis of a finished call. "audio" skips body language and
 * is faster. Running it again replaces the last result.
 */
export function startAnalysis(
  id: string,
  mode: AnalysisMode = 'audio_video',
): Promise<AnalysisStatus> {
  return request<AnalysisStatus>(`/api/sessions/${encodeURIComponent(id)}/analyze`, {
    method: 'POST',
    body: { mode },
  });
}

/** The status and stage while it runs, and the result once complete. */
export function getAnalysis(id: string): Promise<Analysis> {
  return request<Analysis>(`/api/sessions/${encodeURIComponent(id)}/analysis`);
}
