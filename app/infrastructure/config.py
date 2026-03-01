import os
from pathlib import Path

BASE_URL = os.getenv("OPENAI_BASE_URL", "https://llm.scads.ai/v1")
API_KEY = os.getenv("SCADS_API_KEY") or os.getenv("OPENAI_API_KEY")

LANGUAGE_MODEL_NAME = os.getenv("LANGUAGE_MODEL_NAME", "Qwen/Qwen3-VL-8B-Instruct")
FOLLOWUP_MODEL_NAME = os.getenv("FOLLOWUP_MODEL_NAME", LANGUAGE_MODEL_NAME)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-4B")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
TOP_K = int(os.getenv("TOP_K", "3"))

TOKENIZER_DIR = os.getenv("TOKENIZER_DIR", "tokenizers/Qwen3-Embedding-4B")

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../ikmas
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
SQLITE_DB_PATH = Path(os.getenv("SQLITE_DB_PATH", DATA_DIR / "ikmas.db"))

UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
