# Retrieval

IKMAS uses ChromaDB for source-document chunks and an external rerank endpoint for passage ordering.

## Modules

| Module | Responsibility |
|---|---|
| `app/rag/storage.py` | Store, list, hash, dedupe, replace/rename/delete uploaded files |
| `app/rag/ingest.py` | Extract files and split extracted documents into chunks |
| `app/rag/extractors/*` | PDF, text, Markdown, DOCX, PPTX, image extraction |
| `app/rag/tokenizer.py` | Load local tokenizer for token-based splitting |
| `app/rag/vectorstore.py` | Chroma collection access, add, retrieve, clear |
| `app/rag/retriever.py` | Similarity retrieval plus reranking |
| `app/rag/reranker.py` | POST to OpenAI-compatible `/rerank` endpoint |
| `app/backend/retrieval.py` | Normalize chunks and compute retrieval confidence |

## Ingestion Lifecycle

1. `save_upload(...)` writes files to `data/uploads/<collection_id>/`.
2. `split_file(...)` chooses an extractor by suffix.
3. Extracted `Document` metadata receives `file_id` and `source`.
4. `split_documents(...)` uses `RecursiveCharacterTextSplitter.from_huggingface_tokenizer(...)`.
5. `add_docs(...)` sanitizes metadata for Chroma and persists chunks.

Supported file types in the implemented extraction path:

- `.pdf`
- `.txt`
- `.md`
- `.docx`
- `.pptx`
- `.png`
- `.jpg`
- `.jpeg`
- `.webp`

## Query Lifecycle

1. `retrieve(collection_name, query, k)` runs Chroma similarity search.
2. `rerank(query, passages, top_n)` calls `BASE_URL + "/rerank"` with `RERANK_MODEL`.
3. Reranker scores are attached as `doc.metadata["rerank_score"]`.
4. `run_retrieval(...)` normalizes scores, computes confidence, and converts each `Document` into a chunk dict.

Returned chunk shape:

```python
{
    "chunk_id": "...",
    "text": "...",
    "source": "...",
    "title": None,
    "page": None,
    "score": 0.0,
    "metadata": {...},
}
```

## Confidence

`compute_confidence(...)` combines:

- `top1`: highest rerank score
- `avg_top3`: mean of top three scores, or all scores if fewer
- `coverage`: fraction of top five scores above `0.5`

Formula:

```text
confidence = 0.6 * top1 + 0.3 * avg_top3 + 0.1 * coverage
```

No retrieved docs produce zero scores and an empty chunk list.
