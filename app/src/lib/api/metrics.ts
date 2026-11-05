/**
 * The `metrics` of an analysis result, from backend/ai (speech, voice and
 * vision reports). Every field is optional: a part that was skipped, or an
 * older result, may leave any of them out, and the charts show what is there.
 * Large per-sample arrays (pitch.hz, loudness.db) are not typed on purpose:
 * the charts use the windows.
 */

export type TimeWindow = { t_start_s: number; t_end_s: number };

export type VoiceMetrics = {
  pitch?: {
    mean_hz?: number;
    range_semitones?: number;
    windows?: (TimeWindow & { mean_hz: number; std_hz?: number })[];
  };
  loudness?: {
    mean_db?: number;
    windows?: (TimeWindow & { mean_db: number })[];
  };
  speaking_rate?: {
    global_sps?: number;
    windows?: (TimeWindow & { syllables_per_s: number })[];
  };
  intonation?: { monotone_fraction?: number; pitch_range_semitones?: number };
};

export type SpeechMetrics = {
  fluency?: {
    wpm_mean?: number;
    wpm_windows?: { t_start_ms: number; t_end_ms?: number; wpm: number }[];
    filler_total?: number;
    filler_per_min?: number;
    filler_counts?: { word: string; count: number }[];
    pauses?: { start_ms: number; end_ms: number; is_hesitation: boolean }[];
  };
  articulation?: { words_checked?: number; flags?: unknown[] };
};

export type VisionMetrics = {
  pose?: { good_posture_pct?: number; mean_shoulder_tilt_deg?: number };
  eye_contact?: { contact_pct?: number };
  movement?: { gestures_per_min?: number; movement_level?: string };
  emotion?: { dominant_emotion?: string; emotion_distribution?: Record<string, number> };
};

export type Metrics = {
  voice?: VoiceMetrics;
  speech?: SpeechMetrics;
  vision?: VisionMetrics;
};

function record(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

/** The typed metrics, or empty parts where the result has none. */
export function readMetrics(raw: Record<string, unknown> | null | undefined): Metrics {
  return {
    voice: record(raw?.voice) as VoiceMetrics | undefined,
    speech: record(raw?.speech) as SpeechMetrics | undefined,
    vision: record(raw?.vision) as VisionMetrics | undefined,
  };
}
