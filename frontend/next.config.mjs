/** @type {import('next').NextConfig} */
const backend = process.env.TT_BACKEND_ORIGIN || "http://127.0.0.1:8000";

const nextConfig = {
  // Proxy API calls to the FastAPI backend so browser requests are same-origin
  // and HttpOnly session cookies work without CORS.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
