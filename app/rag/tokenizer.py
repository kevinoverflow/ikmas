from __future__ import annotations

import os 
from functools import lru_cache
from typing import List
from transformers import AutoTokenizer

from app.infrastructure.config import TOKENIZER_DIR

def _force_offline():
    # Prevent accidental HF network calls
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

@lru_cache(maxsize=1)
def get_tokenizer():
    _force_offline()
    tok = AutoTokenizer.from_pretrained(
        TOKENIZER_DIR,
        local_files_only=True,
        use_fast = True,
        trust_remote_code= False
    )
    return tok

def count_tokens(text: str) -> int:
    tok = get_tokenizer()
    return len(tok.encode(text, add_special_tokens=False))