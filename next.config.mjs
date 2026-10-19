import { fileURLToPath } from "node:url";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Pin the project root to this folder instead of letting Next.js guess from lockfiles
  // in parent directories.
  outputFileTracingRoot: fileURLToPath(new URL(".", import.meta.url)),

  // /api/* is proxied to the FastAPI backend by app/api/[...path]/route.ts, which reads
  // TT_BACKEND_ORIGIN at request time (deploy hosts may not expose env vars at build).
};

export default nextConfig;
