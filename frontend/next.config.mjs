/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  /** Same-origin proxy so the browser never calls :8000 directly (fixes Docker / CORS / localhost quirks). */
  async rewrites() {
    const backend =
      process.env.BACKEND_INTERNAL_URL ||
      process.env.INTERNAL_API_URL ||
      "http://127.0.0.1:8000";
    const base = backend.replace(/\/$/, "");
    return [{ source: "/api/backend/:path*", destination: `${base}/:path*` }];
  },
};

export default nextConfig;
