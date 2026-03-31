# Retrieval

## Overview

The `retrieval.py` module acts as a **backend wrapper around the RAG pipeline**.

It does **not perform retrieval itself**, but:

- Calls the existing retrieval + reranking logic
- Extracts and normalizes relevance scores
- Computes a **confidence metric**
- Converts raw documents into a **standardized chunk format**
- Returns a structured result for the orchestrator

---

## Role in the Architecture

```
User Input
   ↓
Orchestrator
   ↓
Retrieval Layer (this module)
   ↓
RAG Retriever + Reranker
   ↓
Structured Result + Confidence
   ↓
LLM Decision Logic
```

This module bridges the gap between:

- **Low-level retrieval (LangChain, vector store)**
- **High-level orchestration (roles, FSM, JSON output)**

---

## Key Responsibilities

### 1. Run Retrieval + Reranking

```
retrieve_and_rerank(...)
```

- Retrieves documents from the vector store
- Applies reranking
- Returns top-k ranked documents

---

### 2. Extract Scores

Each document contains a reranker score:

```
doc.metadata["rerank_score"]
```

The module extracts and normalizes it:

```
defextract_score(doc):
returnnormalize_score(doc.metadata["rerank_score"])
```

---

### 3. Normalize Scores

```
defnormalize_score(score):
returnclamp01(score)
```

Ensures all scores are within:

```
[0.0, 1.0]
```

This prevents instability across different models or APIs.

---

### 4. Compute Coverage

```
coverage= (# of top-k scores ≥ threshold) / k
```

Example:

```
scores = [0.9, 0.8, 0.6, 0.3, 0.2]
coverage = 3 / 5 = 0.6
```

**Purpose:**

- Measures how many results are "good enough"
- Prevents overconfidence from a single strong match

---

### 5. Compute Confidence

Core formula:

```
confidence=0.6*top1+0.3*avg_top3+0.1*coverage
```

Where:

| Metric     | Meaning                     |
| ---------- | --------------------------- |
| `top1`     | Best match                  |
| `avg_top3` | Average quality of top 3    |
| `coverage` | Breadth of relevant results |

---

### Example

```
scores= [0.9,0.8,0.7,0.4,0.2]

top1=0.9
avg_top3=0.8
coverage=0.6

confidence=0.84
```

---

## Confidence Policy (Used by Orchestrator)

| Confidence Range | Behavior                 |
| ---------------- | ------------------------ |
| `< 0.55`         | Ask clarifying questions |
| `0.55–0.75`      | Explain + 1 question     |
| `>= 0.75`        | Direct answer            |

---

## 6. Convert Documents → Chunks

LangChain documents are transformed into a clean internal format:

```
{
"chunk_id":str,
"text":str,
"source":str,
"title":str|None,
"page":int|None,
"score":float,
"metadata":dict
}
```

### Why?

- Decouples from LangChain internals
- Enables:
   - Prompt construction
   - Citations
   - Logging
   - Artefact linking

---

## 7. Final Output

```
{
"chunks": [...],
"top1":float,
"avg_top3":float,
"coverage":float,
"confidence":float,
}
```

This is consumed by the orchestrator.
