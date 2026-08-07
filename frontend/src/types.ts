export type AgentKind = "code" | "docs" | "security";

export interface User {
  id: string;
  login: string;
  name: string | null;
  avatar_url: string | null;
}

export interface ProjectSummary {
  project: string;
  project_name: string;
  owner: string;
  repo: string;
  branch: string;
  folders_count: number;
  files_count: number;
  catalog_path?: string;
}

export interface CatalogFile {
  name: string;
  path: string;
  type: string;
  language?: string;
  symbols?: string[];
}

export interface ProjectCatalog {
  project: string;
  project_name: string;
  owner: string;
  repo: string;
  branch: string;
  folders: string[];
  files: CatalogFile[];
}

export interface AskResponse {
  agent: string;
  model: string | null;
  project: string | null;
  project_name: string | null;
  answer: string;
  sources: string[];
}

export interface UploadResponse {
  message: string;
  filename: string;
  path: string;
  saved: boolean;
  pinecone: boolean;
  chunks: number;
  chars: number;
}

export interface RepoIngestResponse {
  message: string;
  owner: string;
  repo: string;
  project: string;
  project_name: string;
  branch: string;
  files_ingested: number;
  files_skipped: number;
  chunks: number;
  pinecone: boolean;
  files: Record<string, unknown>[];
  catalog: ProjectCatalog;
  catalog_path: string;
}

export interface ChatTurn {
  id: string;
  question: string;
  response?: AskResponse;
  error?: string;
  pending?: boolean;
}
