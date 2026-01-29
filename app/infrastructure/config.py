import os

BASE_URL = os.getenv("OPENAI_BASE_URL", "https://llm.scads.ai/v1")
API_KEY = os.getenv("SCADS_API_KEY") or os.getenv("OPENAI_API_KEY")

LANGUAGE_MODEL_NAME = os.getenv("LANGUAGE_MODEL_NAME", "Qwen/Qwen3-VL-8B-Instruct")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-4B")
TOP_K = int(os.getenv("TOP_K", "3"))

TOKENIZER_DIR = os.getenv("TOKENIZER_DIR", "tokenizers/Qwen3-Embedding-4B")