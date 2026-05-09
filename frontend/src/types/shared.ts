export interface FileNode {
  uuid: string;
  name: string;
  type: string;
  is_folder: boolean;
  children?: FileNode[];
  file_details?: {
    uuid: string;
    title: string;
    file_type: string;
    path: string;
    is_promoted: boolean;
    promoted_at: string | null;
    timeline_event_uuids: string[];
    trust_level: string;
    conversion_status: string;
    markdown_path: string | null;
    has_md_twin: boolean;
  };
}

export interface LayoutProps {
  caseId: string;
  userParty: string;
  onCaseSelect: (caseId: string) => void;
  onToggleFullTimeline?: () => void;
}
