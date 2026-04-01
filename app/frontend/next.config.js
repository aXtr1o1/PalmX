/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone', // Optimized for Docker
    async rewrites() {
        const isDev = process.env.NODE_ENV !== 'production';
        // Configure backend from env so you can use localhost/IP on dev and the right URL on Vercel.
        // Recommended: set `NEXT_PUBLIC_BACKEND_URL` in your environment.
        const backendUrl =
            'http://localhost:8000';

        console.log(`[Next.js] Proxying API requests to: ${backendUrl}`);

        return [
            {
                source: '/api/:path*',
                destination: `${backendUrl}/api/:path*`,
            },
            {
                source: '/admin-api/:path*',
                destination: `${backendUrl}/api/admin/:path*`,
            },
            {
                source: '/admin/:path*',
                destination: `${backendUrl}/api/admin/:path*`,
            },
        ]
    },
}

module.exports = nextConfig

