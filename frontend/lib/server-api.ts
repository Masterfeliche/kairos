// Server-side data access for the student site.
// In dev the Next server fetches the FastAPI backend directly (the browser uses the
// /api rewrite instead). Draft preview is opt-in via TT_ALLOW_DRAFT_PREVIEW.
const BASE = process.env.TT_API_BASE || "http://127.0.0.1:8000";

export const PREVIEW = process.env.TT_ALLOW_DRAFT_PREVIEW === "true";

export function withPreview(path: string): string {
  if (!PREVIEW) return path;
  return path.includes("?") ? `${path}&preview=1` : `${path}?preview=1`;
}

export async function serverApi<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${withPreview(path)}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
