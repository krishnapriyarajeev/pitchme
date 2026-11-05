import type { AnalysisMode, AnalysisStatus } from '@/lib/api';

/** The analysis job's stages, in order (backend/server/jobs and ai/analysis). */
export const REVIEW_STAGES = [
  { key: 'preparing', label: 'Getting your recording' },
  { key: 'transcribing', label: 'Writing down what was said' },
  { key: 'analyzing', label: 'Checking your answers and delivery' },
  { key: 'finishing', label: 'Putting your debrief together' },
] as const;

export type StageState = 'done' | 'active' | 'pending';

/**
 * Where each stage is, from the job's real status. A queued job has started
 * none; a running one is at its reported stage.
 */
export function stageStates(status: Pick<AnalysisStatus, 'status' | 'stage'>): StageState[] {
  if (status.status === 'complete') return REVIEW_STAGES.map(() => 'done');
  if (status.status !== 'running') return REVIEW_STAGES.map(() => 'pending');
  const at = Math.max(
    0,
    REVIEW_STAGES.findIndex((stage) => stage.key === status.stage),
  );
  return REVIEW_STAGES.map((_, i) => (i < at ? 'done' : i === at ? 'active' : 'pending'));
}

export const REVIEW_MODES: {
  mode: AnalysisMode;
  title: string;
  detail: string;
  icon: 'mic' | 'video';
}[] = [
  {
    mode: 'audio_video',
    title: 'Audio and video',
    detail: 'Your answers, your voice and pace, and your body language.',
    icon: 'video',
  },
  {
    mode: 'audio',
    title: 'Audio only',
    detail: 'Your answers, your voice and pace. Faster, with no body language.',
    icon: 'mic',
  },
];
