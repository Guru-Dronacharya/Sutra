export type UserRole = "admin" | "compliance_officer" | "engineer" | "auditor";
export type RiskTier = "low" | "medium" | "high" | "prohibited";
export type EUTier = "minimal" | "limited" | "high" | "unacceptable";
export type ExposureProfile = "india_only" | "india_plus_eu";
export type PIIAction = "redact" | "tokenize" | "block";
export type InjectionAction = "log" | "redact_and_log" | "block_and_alert";
export type AuditDecision = "allowed" | "redacted" | "blocked";
export type AuditDirection = "request" | "response";
export type FindingStatus = "covered" | "partially_covered" | "gap";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface AIModel {
  id: string;
  name: string;
  owner: string;
  description?: string;
  provider: string;
  endpoint_url?: string;
  eu_exposure: boolean;
  current_tier: RiskTier;
  eu_tier?: EUTier;
  tiering_logic_version: string;
  needs_review: boolean;
  active_proxy_target: boolean;
  created_at: string;
}

export interface RationalePrinciple {
  key: string;
  framework: string;
  sutra: string;
  pillar: string;
  description: string;
}

export interface FactorRationale {
  factor: string;
  points?: number;
  category?: string;
  reason: string;
  rule?: string;
  principles: RationalePrinciple[];
  escalated_to?: string;
}

export interface RiskAssessment {
  id: string;
  model_id: string;
  answers: Record<string, any>;
  computed_tier: RiskTier;
  eu_tier?: EUTier;
  score: number;
  category_scores?: Record<string, number>;
  rationale: FactorRationale[];
  eu_rationale?: string;
  tiering_logic_version: string;
  override_tier?: RiskTier;
  override_justification?: string;
  overridden_by?: string;
  created_at: string;
}

export interface AuditEntry {
  id: number;
  ts: string;
  model_id: string;
  client_id?: string;
  request_id: string;
  direction: AuditDirection;
  decision: AuditDecision;
  tier: RiskTier;
  pii_entities: Record<string, number>;
  injection_score: number;
  injection_flag: boolean;
  payload_digest: string;
  prev_hash: string;
  entry_hash: string;
}

export interface AuditVerifyResult {
  intact: boolean;
  checked: number;
  first_break_id: number | null;
  broken_range: [number, number] | null;
  verification_time_ms: number;
  message: string;
}

export interface Finding {
  id: string;
  cited_instrument: string;
  cited_section: string;
  status: FindingStatus;
  obligation_summary: string;
  evidence_excerpt?: string;
  policy_location: string;
  remediation_note?: string;
  confidence: number;
}

export interface GapReport {
  report_id: string;
  model_id: string;
  tier: RiskTier;
  exposure_profile: ExposureProfile;
  summary: {
    total_obligations: number;
    covered: number;
    partially_covered: number;
    gap: number;
    coverage_percentage: number;
    instrument_breakdown: Record<string, { covered: number; partially_covered: number; gap: number; total: number }>;
    disclaimer: string;
  };
  created_at: string;
  findings?: Finding[];
}
