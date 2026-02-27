from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

from app.infrastructure.config import EMBEDDING_MODEL, TOP_K, BASE_URL, API_KEY
from app.rag.vectorstore import retrieve, retrieve_mmr
from app.rag.reranker import rerank

def build_inmemory_retriever(docs):
    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        check_embedding_ctx_length=False
    )

    vs = InMemoryVectorStore.from_documents(docs, embedding=embeddings)
    return vs.as_retriever(search_kwargs={"k": TOP_K})

def retrieve_and_rerank(
    collection_name: str,
    query: str,
    k_retrieve: int = 30,
    k_final: int = 5,
    use_mmr: bool = False,
):
    docs = retrieve_mmr(collection_name, query, k=k_retrieve, fetch_k=max(k_retrieve * 2, 20)) if use_mmr else retrieve(collection_name, query, k=k_retrieve)
    if not docs:
        return []

    passages = [d.page_content for d in docs]

    results = rerank(query=query, passages=passages, top_n=k_final)

    # results: list of {"index": i, "relevance_score": s}
    ranked_docs = []
    for item in results:
        idx = item.get("index")
        if idx is None:
            continue
        idx = int(idx)
        if idx < 0 or idx >= len(docs):
            continue
        d = docs[idx]
        # attach score for debugging/citations
        d.metadata["rerank_score"] = item.get("relevance_score")
        ranked_docs.append(d)

    return ranked_docs
