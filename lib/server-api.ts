// Server-side data access for the student site: server components fetch the FastAPI
// backend directly (the browser goes through the /api proxy instead). Draft preview is
// opt-in via TT_ALLOW_DRAFT_PREVIEW.
import { backendBase } from "@/lib/backend";

export const PREVIEW = process.env.TT_ALLOW_DRAFT_PREVIEW === "true";

export function withPreview(path: string): string {
  if (!PREVIEW) return path;
  return path.includes("?") ? `${path}&preview=1` : `${path}?preview=1`;
}

export async function serverApi<T>(path: string): Promise<T | null> {
  const base = backendBase("server");
  if (!base) return null;
  try {
    const res = await fetch(`${base}${withPreview(path)}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
