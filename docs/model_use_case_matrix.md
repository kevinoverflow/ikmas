# Model Use Case Matrix

This document records the model categories relevant to the current codebase. It is not an authoritative benchmark. Provider model availability and latency can change, so verify available models against the configured OpenAI-compatible endpoint before relying on a specific name.

## Models Used by Code Defaults

| Use case | Config variable | Default |
|---|---|---|
| General chat / role answers | `LANGUAGE_MODEL_NAME` or role-specific variables | `Qwen/Qwen3-Coder-30B-A3B-Instruct` |
| Router backend default | `ROUTER_MODEL_NAME` exists, but `handle_turn(...)` creates the router backend without passing it explicitly | effectively `LANGUAGE_MODEL_NAME` unless changed in code |
| Embeddings | `EMBEDDING_MODEL` | `Qwen/Qwen3-Embedding-4B` |
| Reranking | `RERANK_MODEL` | `BAAI/bge-reranker-v2-m3` |

## Current Runtime Requirements

The configured provider must support:

- chat completions with `response_format={"type": "json_object"}`,
- embeddings compatible with LangChain `OpenAIEmbeddings`,
- reranking at `/rerank` returning either `results` or `data` with `index` and `relevance_score`.

## Practical Selection Guidance

- Use a reliable JSON-capable chat model for routing and answers.
- Use a model with enough context length for retrieved chunks plus role instructions.
- Keep embedding model and local tokenizer aligned when possible.
- Keep rerank responses fast; retrieval blocks every chat turn.
- Use `model_override` from the UI for experiments, but document stable defaults in environment variables.
