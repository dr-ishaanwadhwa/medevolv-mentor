import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['three'],
  // standalone server for deploy/v2 (built on the Mac, run with node on the VM); trace from the pnpm workspace root
  output: 'standalone',
  outputFileTracingRoot: path.join(here, '../..'),
  async redirects() {
    // Ask moved to /ask (PRD 4.L, D-6). Old /?q=...&go=1 links keep working: Next passes the query string through.
    return [{ source: '/', has: [{ type: 'query', key: 'q' }], destination: '/ask', permanent: false }];
  },
  async rewrites() {
    // dev only in practice: in production Caddy sends /api/* straight to FastAPI (no buffering of SSE)
    const backendUrl = process.env.BACKEND_API_URL || 'http://127.0.0.1:8000';
    return [{ source: '/api/:path*', destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
