import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = BASE_DIR / "docs"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"

load_dotenv(BASE_DIR / ".env")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "250"))
TOP_K = int(os.getenv("TOP_K", "5"))

if not DEEPSEEK_API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY não definida no .env")
