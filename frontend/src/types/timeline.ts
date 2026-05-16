// Timeline Event Types
export type Status =
  | "UNDISPUTED"
  | "CONTESTED"
  | "REFUTED"
  | "STIPULATED"
  | "PENDING";
export type SourceParty =
  | "CLIENT"
  | "OPPOSING"
  | "NEUTRAL"
  | "COURT"
  | "WITNESS";
export type Category =
  | "contract"
  | "email"
  | "court_filing"
  | "communication"
  | "meeting"
  | "deadline"
  | "verified"
  | "contested"
  | "personal"
  | "legal"
  | "medical"
  | "financial"
  | "education"
  | "other";

// Archive Document
export interface ArchiveDocument {
  id: string;
  title: string;
  file_type: string;
  file_url: string;
  path: string;
  category: string;
}

// Timeline Event
export interface TimelineEvent {
  id: string;
  date: string;
  event: string;
  category: Category;
  source_type: string;
  status: Status;
  source_party: SourceParty;
  citation: string;
  notes: string;
  version: number;
  created_at: string;
  updated_at: string;
  evidence: ArchiveDocument[];
  replaces_event: string | null;
  counter_claims: string[];
  case: string;
  case_id: string;
  created_by: string;
  created_by_username: string;
  timeline_file: string | null;
  // Phase 2: System source fields
  is_system_source: boolean;
  trust_level: number;
  has_gold_seal: boolean;
  // Section header from Markdown ## headers
  section_header?: string | null;
  // Citation data from last PDF generation
  last_printed_citation?: {
    page_number: number | null;
    row_index: number;
  } | null;
}

// Contested Pair
export interface ContestedPair {
  left: TimelineEvent;
  right: TimelineEvent;
  diff: {
    category: boolean;
    status: boolean;
    notes: boolean;
    citation: boolean;
    evidence: boolean;
  };
}

// Diff View Data
export interface DiffViewData {
  left_party: SourceParty;
  right_party: SourceParty;
  shared: TimelineEvent[];
  left_only: TimelineEvent[];
  right_only: TimelineEvent[];
  contested: Record<string, ContestedPair>;
}

// Timeline Collection
export interface TimelineCollection {
  id: string;
  name: string;
  description: string;
  events: TimelineEvent[];
  case: string;
  case_id: string;
  created_by: string;
  created_by_username: string;
  created_at: string;
  updated_at: string;
  is_public: boolean;
  event_count: number;
}

// API Response Types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

// Filter Types
export interface TimelineFilters {
  party?: SourceParty;
  status?: Status;
  category?: Category;
  start_date?: string;
  end_date?: string;
  has_evidence?: boolean;
  contested?: boolean;
  filter_noise?: boolean;
  min_significance?: number;
}

// User Party Context
export interface UserContext {
  party: SourceParty;
  canContest: (event: TimelineEvent) => boolean;
}

// AI Research Perspective
export type PerspectiveMode = 'CLIENT' | 'NEUTRAL' | 'OPPOSING';
