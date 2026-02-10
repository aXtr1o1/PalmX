/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone', // Optimized for Docker
    async rewrites() {
        // If running in Docker (production), default to backend service name if env is missing.
        // If local dev, default to localhost.
        const isDev = process.env.NODE_ENV !== 'production';
        const backendUrl = process.env.BACKEND_URL || (isDev ? 'http://127.0.0.1:8000' : 'http://backend:8000');

        console.log(`[Next.js] Proxying API requests to: ${backendUrl}`);

        return [
            {
                source: '/api/:path*',
                destination: `${backendUrl}/api/:path*`,
            },
            {
                source: '/admin-api/:path*',
                destination: `${backendUrl}/admin/:path*`,
            },
        ]
    },
}

module.exports = nextConfig
