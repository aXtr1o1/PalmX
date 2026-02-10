FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
# ENV BACKEND_URL will be passed at runtime, but Next.js usage in rewrites is server-side so it works.
# Build standalone
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/.next/standalone ./

EXPOSE 3000
# server.js is the entrypoint for standalone build
CMD ["node", "server.js"]
