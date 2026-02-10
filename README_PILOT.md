# PalmX Pilot - Setup & Run Instructions

## 1. Environment Setup

Copy the example `.env` file and fill in your Azure OpenAI keys (or OpenAI fallback):

```bash
cp .env.example .env
# Edit .env with your real API keys
```

## 2. Backend Setup

Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn openai azure-identity faiss-cpu rapidfuzz portalocker openpyxl python-dotenv
```

Build the Search Index (RAG):

```bash
./run_build_index.sh
```
*Note: This generates `runtime/index/faiss.index` from `engine-KB/PalmX-buyerKB.csv`.*

Run the Backend Server:

```bash
./run_backend.sh
```
*Server runs at `http://127.0.0.1:8000`*

## 3. Frontend Setup

In a new terminal:

```bash
./run_frontend.sh
```
*App runs at `http://localhost:3000`*

## 4. Usage

- **Chat Interface**: Open `http://localhost:3000`
- **Admin Dashboard**: Open `http://localhost:3000/admin`
  - Default password: `admin` (or whatever you set in `.env`)

## 5. Artifacts
- **Leads CSV**: `runtime/leads/leads.csv`
- **Audit Logs**: `runtime/leads/audit.csv`
- **Excel Exports**: `runtime/exports/`
