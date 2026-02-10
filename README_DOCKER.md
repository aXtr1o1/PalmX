# PalmX - Docker Guide

Full system dockerization (Frontend + Backend + RAG).

## Prerequisites
- Docker & Docker Compose installed.
- Valid `.env` file (copy from `.env.example`).

## 🚀 One-Click Run

```bash
./run_docker.sh
```

This script will:
1. Check environment.
2. Build images (frontend + backend).
3. Start services in the background.

## 🛠️ Management Commands

Once running, use standard Docker Compose commands:

- **View Logs**: `docker-compose logs -f`
- **Stop System**: `docker-compose down`
- **Restart**: `docker-compose restart`

## Service Endpoints
- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Admin**: [http://localhost:3000/admin](http://localhost:3000/admin)
