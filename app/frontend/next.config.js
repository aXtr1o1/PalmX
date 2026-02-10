/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone', // Optimized for Docker
    async rewrites() {
        // If running in Docker, BACKEND_URL provided via env (e.g., http://backend:8000)
        // If local dev, fallback to localhost:8000
        const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
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
