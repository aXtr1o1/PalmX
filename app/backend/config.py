import os
from dotenv import load_dotenv

# Load .env from repo root
load_dotenv()

class Config:
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4")
    AZURE_OPENAI_EMBED_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-ada-002")

    # OpenAI Fallback
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

    # Paths
    BASE_DIR = os.getcwd()
    KB_CSV_PATH = os.path.join(BASE_DIR, os.getenv("KB_CSV_PATH", "engine-KB/PalmX-buyerKB.csv"))
    RUNTIME_DIR = os.path.join(BASE_DIR, os.getenv("RUNTIME_DIR", "runtime"))
    INDEX_PATH = os.path.join(RUNTIME_DIR, "index/faiss.index")
    META_PATH = os.path.join(RUNTIME_DIR, "index/meta.json")
    LEADS_PATH = os.path.join(RUNTIME_DIR, "leads/leads.csv")
    AUDIT_PATH = os.path.join(RUNTIME_DIR, "leads/audit.csv")

    # Admin
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

    # Ensure runtime dirs exist
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(LEADS_PATH), exist_ok=True)
    os.makedirs(os.path.join(RUNTIME_DIR, "exports"), exist_ok=True)
