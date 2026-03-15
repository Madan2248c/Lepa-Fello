import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api-proxy/:path*",
        destination: "http://52.66.75.37:8000/:path*",
      },
      {
        source: "/agent-proxy/:path*",
        destination: "http://52.66.75.37:8001/:path*",
      },
    ];
  },
};

export default nextConfig;
