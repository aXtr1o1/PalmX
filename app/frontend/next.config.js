/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone', // Optimized for Docker
    async rewrites() {
        const isDev = process.env.NODE_ENV !== 'production';
        const backendUrl = process.env.BACKEND_URL || (isDev ? 'http://127.0.0.1:8000' : 'http://20.224.153.225:8000');

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
            {
                source: '/admin/:path*',
                destination: `${backendUrl}/admin/:path*`,
            },
        ]
    },
}

module.exports = nextConfig

