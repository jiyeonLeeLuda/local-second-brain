import type { NextConfig } from "next";

/**
 * 브라우저는 항상 같은 origin의 `/api/*`만 호출하고,
 * Next.js 서버가 FastAPI 백엔드로 프록시한다 (CORS 설정 불필요).
 *
 * 주의: rewrites 대상은 `next build` 시점에 routes-manifest로 고정된다.
 * BACKEND_URL을 바꿨다면 dev는 재시작, prod는 재빌드해야 한다.
 */
const backendUrl = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  // Self-contained server bundle for the Docker image (see Dockerfile).
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  experimental: {
    // 로컬 LLM 응답은 수십 초가 걸릴 수 있다. 기본 프록시 타임아웃(30초)을 늘린다.
    proxyTimeout: 180_000,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
