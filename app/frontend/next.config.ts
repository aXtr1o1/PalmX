import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    // Configure backend from env so you can use localhost/IP on dev and the right URL on Vercel.
    // Recommended: set `NEXT_PUBLIC_BACKEND_URL` in your environment.
    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL ||
      process.env.BACKEND_URL ||
      "http://localhost:8000";

    console.log(`[Next.js] Proxying API requests to: ${backendUrl}`);

    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/admin-api/:path*",
        destination: `${backendUrl}/api/admin/:path*`,
      },
      {
        source: "/admin/:path*",
        destination: `${backendUrl}/api/admin/:path*`,
      },
    ];
  },
};

export default nextConfig;
