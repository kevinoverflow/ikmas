# Model Configuration

Model and provider settings live in `app/infrastructure/config.py`.

## Provider

```text
OPENAI_BASE_URL default: https://llm.scads.ai/v1
API key: SCADS_API_KEY or OPENAI_API_KEY
```

The code uses OpenAI-compatible chat, embedding, and rerank APIs.

## Chat Models

Default:

```text
GLOBAL_MODEL_OVERRIDE=Qwen/Qwen3-Coder-30B-A3B-Instruct
LANGUAGE_MODEL_NAME=<GLOBAL_MODEL_OVERRIDE>
```

Role-specific environment variables:

- `ROUTER_MODEL_NAME`
- `SCRIBE_MODEL_NAME`
- `SEMANTIC_LINKING_MODEL_NAME`
- `MENTOR_MODEL_NAME`
- `CONTEXT_RECONSTRUCTOR_MODEL_NAME`
- `LANGUAGE_MODEL_NAME`

Current implementation detail: `model_selection_for_role(...)` uses the role-specific variables for answer model selection, and a UI `model_override` can override the answer model. `OpenAIChatBackend()` without an explicit model uses `LLM_MODEL_NAME`; the router backend is created this way in `handle_turn(...)`.

## Embedding and Rerank

Defaults:

```text
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
RERANK_MODEL=BAAI/bge-reranker-v2-m3
TOP_K=5
TOKENIZER_DIR=tokenizers/Qwen3-Embedding-4B
```

Embedding calls are made through LangChain `OpenAIEmbeddings`. Reranking is a POST to `BASE_URL + "/rerank"`.

## Data Paths

```text
DATA_DIR=<repo>/data
UPLOAD_DIR=<DATA_DIR>/uploads
CHROMA_DIR=<DATA_DIR>/chroma
DB_PATH=data/ikmas.db
```

`UPLOAD_DIR` and `CHROMA_DIR` are created at import time.
