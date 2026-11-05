/**
 * What the API sends and takes. These follow backend/server/schemas; keep
 * the two in step. Times are ISO 8601 strings.
 */

// ---- auth ----

export type AuthResponse = { access_token: string; token_type: 'bearer'; user_id: string };

// ---- profile ----

export type UploadKind = 'voice' | 'playbook';
export type CloneStatus = 'pending' | 'ready' | 'failed';

export type Profile = {
  id: string;
  email: string;
  display_name: string | null;
  role_title: string | null;
  sells: string | null;
  has_voice_sample: boolean;
  /** Presigned and short-lived: read it again rather than keep it. */
  voice_sample_url: string | null;
  voice_clone_id: string | null;
  /** null until a voice sample is uploaded. */
  voice_clone_status: CloneStatus | null;
  voice_clone_error: string | null;
  has_playbook: boolean;
  playbook_url: string | null;
  created_at: string;
};

/** Only the fields sent are changed. */
export type ProfileUpdate = {
  display_name?: string;
  role_title?: string;
  sells?: string;
};

export type UploadUrl = { upload_url: string; object_key: string; expires_in_seconds: number };

export type UploadConfirm = {
  kind: UploadKind;
  object_key: string;
  url: string;
  voice_clone_id: string | null;
  voice_clone_status: CloneStatus | null;
};

export type VoiceClone = { status: CloneStatus | null; error: string | null };

// ---- sessions ----

export type SessionState = 'waiting' | 'active' | 'complete' | 'failed';
export type EndReason = 'seller_left' | 'time_limit' | 'no_show' | 'error' | 'lost';
export type AnalysisState = 'not_started' | 'queued' | 'running' | 'complete' | 'failed';
export type AnalysisMode = 'audio' | 'audio_video';

/** The deal from the prepare screen. Choices are keys from constants/deal. */
export type NewSession = {
  prospect_name: string;
  company: string;
  industry?: string;
  deal_stage?: string;
  buyer_composure?: string;
  competitors?: string;
  audience_type?: string;
};

export type CallRoom = {
  session_id: string;
  room_name: string;
  /** Join the room with this token soon; it expires. */
  token: string;
  livekit_url: string;
};

export type TranscriptTurn = {
  role: 'seller' | 'buyer';
  text: string;
  start_ms: number;
  end_ms: number;
  interrupted: boolean;
};

export type SessionSummary = {
  session_id: string;
  status: SessionState;
  prospect_name: string;
  company: string;
  deal_stage: string;
  duration_seconds: number | null;
  created_at: string;
  analysis_status: AnalysisState;
  /** 0 to 100, once the analysis is complete. */
  overall_score: number | null;
};

export type SessionDetail = SessionSummary & {
  industry: string | null;
  buyer_composure: string | null;
  competitors: string | null;
  audience_type: string | null;
  transcript: TranscriptTurn[];
  recording_url: string | null;
  started_at: string | null;
  ended_at: string | null;
  end_reason: EndReason | null;
};

// ---- analysis ----

export type Severity = 'info' | 'low' | 'medium' | 'high';

export type Dimension = {
  name: string;
  label: string;
  /** null when it could not be scored; `skipped` says why. */
  score: number | null;
  summary: string;
  skipped: string | null;
};

export type Finding = {
  pipeline: string;
  category: string;
  severity: Severity;
  summary: string;
  note: { t_start_ms: number; t_end_ms: number; quote: string } | null;
  details: Record<string, unknown>;
};

export type CorrectedAnswer = {
  question: string;
  original: string;
  stronger: string;
  change: string;
  citation: string;
  verified: boolean;
  unsupported_numbers: string[];
  t_start_ms: number | null;
  /** In the user's cloned voice; null with no voice clone. */
  audio_url: string | null;
};

export type AnalysisResult = {
  overall_score: number | null;
  dimensions: Dimension[];
  summary: string;
  findings: Finding[];
  strengths: string[];
  prep_list: string[];
  corrected_answers: CorrectedAnswer[];
  questions: number;
  handled: number;
  metrics: Record<string, unknown>;
  annotated_video_url: string | null;
  notes: string[];
};

export type AnalysisStatus = {
  status: AnalysisState;
  /** transcribing, analyzing or finishing while it runs. */
  stage: string | null;
  /** A plain message when it failed. */
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export type Analysis = AnalysisStatus & { result: AnalysisResult | null };
