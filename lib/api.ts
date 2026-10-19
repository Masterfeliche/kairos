export type Role = "admin" | "reviewer" | "owner" | "cr";

export type Admin = { id: string; email: string; role: Role; display_name?: string | null; cohorts?: any[] };

export type Version = {
  id: string;
  period_id: string;
  label: string;
  status: string;
  is_active: boolean;
};

export type VersionDetail = Version & {
  sessions: number;
  open_issues: number;
  open_errors: number;
  pages: number | null;
  source_document_id: string;
};

export type Issue = {
  id: string;
  session_id: string | null;
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
  page: number | null;
  resolved: boolean;
};

export type SessionRow = {
  id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  course_code_raw: string | null;
  course_name_raw: string;
  lecturer_raw: string | null;
  venue_raw: string | null;
  session_type: string | null;
  cohort_codes: string[];
  confidence: string;
  extraction_method: string;
  source_page: number;
  is_shared: boolean;
};

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
  return match ? decodeURIComponent(match[1]) : null;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});
  const isForm = options.body instanceof FormData;
  if (options.body && !isForm) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = readCookie("tt_csrf");
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }

  const res = await fetch(path, { ...options, headers, credentials: "include" });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail)
        : `Request failed (${res.status})`;
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

export const DAYS = ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
