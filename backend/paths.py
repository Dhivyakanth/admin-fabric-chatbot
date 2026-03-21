from pathlib import Path

# Resolve project paths from this file location so imports work from any CWD.
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

DATA_DIR = PROJECT_ROOT / "data"
STORAGE_DIR = PROJECT_ROOT / "storage"
CHAT_HISTORY_DIR = STORAGE_DIR / "chat_history"
CHROMADB_DIR = STORAGE_DIR / "chromadb"
FAISS_INDEX_DIR = CHROMADB_DIR / "faiss_index"
EMAIL_INDEX_PATH = PROJECT_ROOT / "email" / "index.html"
ENV_FILE_PATH = PROJECT_ROOT / ".env"
DATA_CSV_PATH = DATA_DIR / "database_data.csv"