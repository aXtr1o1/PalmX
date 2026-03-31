# PalmX: Premium AI Property Concierge

> **The Intelligent Gateway to Palm Hills Developments.**  
> PalmX is an enterprise-grade AI system designed to transform property discovery and lead acquisition. Exclusive to Palm Hills, it combines robust semantic retrieval with a high-performance sales persona.

---

## Project Identity & Vision

PalmX is not just a chatbot; it is a **Senior AI Property Consultant**. It is built to mirror the prestige and understated luxury of the Palm Hills brand, guiding potential buyers through an integrated portfolio of 45+ flagship projects across Egypt.

**Core Pillars:**
- **Truthfulness**: Grounded in an audited knowledge base of official listings and community amenities.
- **Persuasion**: Engineered with a "Closer" mindset to qualify leads and handle objections seamlessly.
- **Integrity**: Physical data persistence and explicit lead confirmation logic ensure high-fidelity buyer data.

---

## Technical Architecture

### **The Intelligent Backend (FastAPI)**
- **RAG Execution**: A hybrid retrieval pipeline using **FAISS** (semantic) and **RapidFuzz** (fuzzy entity matching).
- **Contextual Routing**: Automated query rewriting that ensures the AI maintains context across complex, multi-turn conversations.
- **Lead Persistence**: Specialized `leads_service` using file locking and `fsync` for immediate, reliable disk commitment.

### **The Premium Frontend (Next.js 14)**
- **Design Language**: Magazine-editorial style with high-contrast Dark Ink and Brand Red accents.
- **Executive Dashboard**: Real-time analytics built with `recharts` for monitoring lead trends and regional site-visit intent.
- **Responsive Streaming**: Low-latency SSE streaming for a premium "instant-thought" user experience.

---

## System Usability & Governance

### **The 6-Stage Sales Machine**
PalmX operates on a strictly governed conversation flow:
1. **Discovery**: Mapping the user's broad real estate goals.
2. **Qualification**: Seamlessly extracting Budget, Region, and Timeline.
3. **Curate**: Matching intent with a data-verified shortlist of projects.
4. **Lifestyle Logic**: Presenting facts as value propositions (ROI, Scarcity, Amenities).
5. **Soft Close**: Proposing concrete next steps (Brochure, Site Visit).
6. **Handover**: Confirming all captured details *before* saving to the CRM/Leads file.

### **Financial Localization**
- **Currency Intelligence**: Automatic normalization of USD/AED inputs into **EGP (Egyptian Pound)** for the master records.

---

## Getting Started

### **Environment Setup**
1. Copy the template: `cp .env.example .env`
2. Configure your Azure OpenAI or OpenAI keys.

### **Run Locally**
```bash
# Terminal 1: Backend
./run_backend.sh

# Terminal 2: Frontend
./run_frontend.sh
```

## Docker Deployment Guide

The entire PalmX ecosystem is fully containerized for seamless, platform-independent deployment.

### **Quick Start**
To build and launch the entire system (Frontend, Backend, and RAG services) with a single command:
```bash
./run_docker.sh
```

### **1. Standard Lifecycle Commands**
Once the system is built, you can manage it using standard `docker-compose` commands:

- **Build and Start (Detached)**:
  ```bash
  docker-compose up --build -d
  ```
- **Stop and Remove Containers**:
  ```bash
  docker-compose down
  ```
- **Restart All Services**:
  ```bash
  docker-compose restart
  ```
- **Stop Services (Keeps Containers)**:
  ```bash
  docker-compose stop
  ```

### **2. Monitoring & Debugging**
- **Follow Live Logs**:
  ```bash
  docker-compose logs -f
  ```
- **View Backend-Only Logs**:
  ```bash
  docker-compose logs -f backend
  ```
- **Inspect Running Containers**:
  ```bash
  docker ps
  ```

### **3. Data Persistence & Architecture**
The Docker setup utilizes **Volumes** to ensure data integrity across container restarts:
- **`./runtime` → `/code/runtime`**: Persists leads, audit logs, and search indices.
- **`./engine-KB` → `/code/engine-KB`**: Syncs the property knowledge base CSV.
- **Environment**: The `.env` file is automatically mapped to provide the backend with API keys and secrets.

### **4. Container Endpoints**
- **Frontend App**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Admin Dashboard**: [http://localhost:3000/admin](http://localhost:3000/admin)

---

## Roadmap & Prospects

- **Voice Concierge**: Real-time, low-latency audio interaction.
- **CRM Webhooks**: Instant bi-directional sync with Salesforce and SAP.
- **Visual RAG**: Integration of floor-plan analysis and virtual tour guidance.

---