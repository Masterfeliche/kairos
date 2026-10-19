// Where the FastAPI backend lives, read at request time (deploy hosts may only provide
// environment variables at runtime).
//
// In development the API runs on http://127.0.0.1:8000 next to `next dev` on :3000.
// In production that default is dangerous: the website itself listens on :8000, so a
// missing setting would make the /api proxy call itself in an endless loop. There the
// setting is required instead.

/** Header the /api proxy adds to requests it forwards, to detect a proxy loop. */
export const PROXY_HOP_HEADER = "x-kairos-proxied";

let warned = false;

export function backendBase(prefer: "proxy" | "server"): string | null {
  const origin = process.env.TT_BACKEND_ORIGIN?.trim();
  const base = process.env.TT_API_BASE?.trim();
  const configured = prefer === "proxy" ? origin || base : base || origin;
  if (configured) return configured.replace(/\/+$/, "");
  if (process.env.NODE_ENV !== "production") return "http://127.0.0.1:8000";
  if (!warned) {
    warned = true;
    console.error(
      "[kairos] TT_API_BASE / TT_BACKEND_ORIGIN is not set: set it to the API URL " +
        "(e.g. https://kairos-api.deploy.tz). API calls will fail until then.",
    );
  }
  return null;
}
