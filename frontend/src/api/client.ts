import type {
  AskResponse,
  AgentKind,
  ProjectCatalog,
  ProjectSummary,
  RepoIngestResponse,
  UploadResponse,
  User,
} from "../types";

const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

const TOKEN_KEY = "qa_agent_token";
const REFRESH_KEY = "qa_agent_refresh_token";
/** Refresh when access token has less than this many seconds left */
const REFRESH_SKEW_SECONDS = 5 * 60;

type TokenListener = (token: string | null) => void;
const tokenListeners = new Set<TokenListener>();

export function getApiUrl() {
  return API_URL;
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
  tokenListeners.forEach((fn) => fn(token));
}

export function setRefreshToken(token: string) {
  localStorage.setItem(REFRESH_KEY, token);
}

export function setTokens(access: string, refresh?: string | null) {
  setToken(access);
  if (refresh) setRefreshToken(refresh);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  tokenListeners.forEach((fn) => fn(null));
}

export function onTokenChange(listener: TokenListener) {
  tokenListeners.add(listener);
  return () => {
    tokenListeners.delete(listener);
  };
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

function decodeJwtPayload(token: string): { exp?: number; token_type?: string } | null {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const normalized = part.replace(/-/g, "+").replace(/_/g, "/");
    const json = atob(normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "="));
    return JSON.parse(json) as { exp?: number; token_type?: string };
  } catch {
    return null;
  }
}

export function accessTokenExpiresSoon(token: string | null = getToken()): boolean {
  if (!token) return true;
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return false;
  const now = Math.floor(Date.now() / 1000);
  return payload.exp - now <= REFRESH_SKEW_SECONDS;
}

let refreshInFlight: Promise<string | null> | null = null;

export async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) {
        clearToken();
        return null;
      }
      const data = (await res.json()) as {
        access_token: string;
        refresh_token?: string;
      };
      setTokens(data.access_token, data.refresh_token ?? refresh);
      return data.access_token;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

/** Ensure access token is fresh; refresh automatically when near expiry. */
export async function ensureFreshToken(): Promise<string | null> {
  const token = getToken();
  if (!token) {
    if (getRefreshToken()) return refreshAccessToken();
    return null;
  }
  if (accessTokenExpiresSoon(token)) {
    const refreshed = await refreshAccessToken();
    // Keep current access token until it actually fails if refresh is unavailable
    return refreshed ?? token;
  }
  return token;
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) {
      return data.detail.map((d: { msg?: string }) => d.msg || String(d)).join("; ");
    }
    return JSON.stringify(data);
  } catch {
    return res.statusText || "Request failed";
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  _retried = false,
): Promise<T> {
  const token = await ensureFreshToken();
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401 && !_retried && getRefreshToken()) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return api<T>(path, options, true);
    }
  }

  if (res.status === 401) {
    clearToken();
    throw new ApiError(401, "Not authenticated. Please sign in again.");
  }

  if (!res.ok) {
    throw new ApiError(res.status, await parseError(res));
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export function githubLoginUrl() {
  return `${API_URL}/auth/github`;
}

export function fetchMe() {
  return api<User>("/auth/me");
}

export function fetchProjects() {
  return api<{ projects: ProjectSummary[] }>("/projects").then((r) => r.projects);
}

export function fetchProject(owner: string, repo: string) {
  return api<ProjectCatalog>(`/projects/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`);
}

export function askQuestion(body: {
  question: string;
  project?: string | null;
  agent?: AgentKind | null;
  context?: string | null;
}) {
  return api<AskResponse>("/ask", {
    method: "POST",
    body: JSON.stringify({
      question: body.question,
      project: body.project || null,
      agent: body.agent || null,
      context: body.context || null,
    }),
  });
}

export function ingestRepo(body: {
  owner: string;
  repo: string;
  branch?: string;
  path_prefix?: string;
}) {
  return api<RepoIngestResponse>("/repos/ingest", {
    method: "POST",
    body: JSON.stringify({
      owner: body.owner,
      repo: body.repo,
      branch: body.branch || null,
      path_prefix: body.path_prefix || "",
    }),
  });
}

export function uploadDocument(file: File) {
  const form = new FormData();
  form.append("file", file);
  return api<UploadResponse>("/documents", {
    method: "POST",
    body: form,
  });
}
