import type { NextRequest } from "next/server";

/**
 * Same-origin proxy for the FastAPI backend: the browser calls /api/* on the website and
 * this forwards it, so HttpOnly session cookies stay first-party and no CORS is needed.
 *
 * The backend address is read at request time (not baked in at build time like a
 * next.config rewrite), because hosts such as deploy.tz may only provide environment
 * variables when the app runs.
 */
export const dynamic = "force-dynamic";

const HOP_BY_HOP = ["connection", "keep-alive", "transfer-encoding", "upgrade", "host", "content-length"];

function backendOrigin(): string {
  return process.env.TT_BACKEND_ORIGIN || process.env.TT_API_BASE || "http://127.0.0.1:8000";
}

async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const target = new URL(`/api/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`, backendOrigin());

  const headers = new Headers(req.headers);
  for (const h of HOP_BY_HOP) headers.delete(h);
  headers.set("x-forwarded-host", req.headers.get("host") ?? req.nextUrl.host);
  headers.set("x-forwarded-proto", req.nextUrl.protocol.replace(":", ""));

  const hasBody = !["GET", "HEAD"].includes(req.method);
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? req.body : undefined,
      redirect: "manual",
      cache: "no-store",
      // Required by Node's fetch to stream a request body.
      ...(hasBody ? { duplex: "half" } : {}),
    } as RequestInit);
  } catch {
    return Response.json({ detail: "The timetable service is unreachable. Try again shortly." }, { status: 502 });
  }

  // fetch() already decoded any compression, so drop the encoding/length it described.
  const out = new Headers(upstream.headers);
  out.delete("content-encoding");
  out.delete("content-length");
  out.delete("transfer-encoding");
  return new Response(upstream.body, { status: upstream.status, statusText: upstream.statusText, headers: out });
}

export const GET = proxy;
export const HEAD = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
