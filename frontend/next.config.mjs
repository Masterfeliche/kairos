import { fileURLToPath } from "node:url";

/** @type {import('next').NextConfig} */
const backend = process.env.TT_BACKEND_ORIGIN || "http://127.0.0.1:8000";

const nextConfig = {
  // The repo root also has a package.json (for hosts that look there), so pin the
  // project root to this folder instead of letting Next.js guess from lockfiles.
  outputFileTracingRoot: fileURLToPath(new URL(".", import.meta.url)),

  // Proxy API calls to the FastAPI backend so browser requests are same-origin
  // and HttpOnly session cookies work without CORS.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
