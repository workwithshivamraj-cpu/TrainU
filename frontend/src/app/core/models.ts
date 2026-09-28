export interface Membership {
  organization_id: string;
  organization_name: string;
  organization_slug: string;
  role: Role;
}

export type Role = 'platform_admin' | 'org_admin' | 'content_owner' | 'contributor' | 'viewer';

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_platform_admin: boolean;
  memberships: Membership[];
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  retention_days: number;
  created_at: string;
}

export interface Member {
  membership_id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface Invitation {
  id: string;
  email: string;
  role: Role;
  status: string;
  expires_at: string;
  token: string;
}

export interface ApplicationModule {
  id: string;
  application_id: string;
  name: string;
  description: string;
  features: string[];
}

export interface Application {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  version: string;
  environment: 'development' | 'uat' | 'production';
  owning_team: string;
  support_contact: string;
  status: 'active' | 'maintenance' | 'retired';
  features: string[];
  created_at: string;
  modules: ApplicationModule[];
}

export type SourceStatus =
  | 'uploaded'
  | 'queued'
  | 'processing'
  | 'awaiting_review'
  | 'approved'
  | 'indexed'
  | 'failed'
  | 'archived';

export interface ProcessingJob {
  id: string;
  stage: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  detail: string;
  error: string | null;
}

export interface SourceSummary {
  id: string;
  organization_id: string;
  application_id: string | null;
  module_id: string | null;
  content_owner_id: string;
  title: string;
  description: string;
  source_type: string;
  status: SourceStatus;
  feature_tag: string;
  application_version: string;
  environment: string | null;
  audience_roles: string[];
  original_filename: string;
  file_size_bytes: number;
  duration_seconds: number | null;
  approved_at: string | null;
  archived_at: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourceDetail extends SourceSummary {
  jobs: ProcessingJob[];
  playback_url: string | null;
}

export interface TranscriptChunk {
  id: string;
  title: string;
  topic: string;
  text: string;
  chunk_index: number;
  start_seconds: number;
  end_seconds: number;
}

export interface Citation {
  source_id: string;
  chunk_id: string;
  source_title: string;
  start_seconds: number;
  end_seconds: number;
  quoted_evidence: string;
  confidence_score: number;
  is_archived: boolean;
}

export interface RelatedClip {
  source_id: string;
  source_title: string;
  topic: string;
  start_seconds: number;
  end_seconds: number;
}

export interface AskResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  steps: string[];
  confidence: 'high' | 'medium' | 'low' | 'none';
  citations: Citation[];
  related_clips: RelatedClip[];
  follow_up_questions: string[];
  /** Client-side only: tracks the feedback the user gave for this answer. */
  __feedback?: 'helpful' | 'not_helpful';
}

export interface ChatTurn {
  role: 'user' | 'assistant';
  question?: string;
  response?: AskResponse;
  pending?: boolean;
}

export interface UsageMetricDay {
  metric_date: string;
  stored_video_minutes: number;
  processed_video_minutes: number;
  questions_asked: number;
  active_users: number;
}

export interface UsageSummary {
  total_stored_video_minutes: number;
  total_processed_video_minutes: number;
  total_questions_asked: number;
  active_users_last_30_days: number;
  daily: UsageMetricDay[];
}

export interface AuditLogEntry {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  description: string;
  actor_user_id: string | null;
  created_at: string;
}

export interface FeedbackEntry {
  id: string;
  message_id: string;
  rating: 'helpful' | 'not_helpful';
  comment: string;
  created_at: string;
}
