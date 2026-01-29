from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

from app.infrastructure.config import EMBEDDING_MODEL, TOP_K, BASE_URL, API_KEY

def build_inmemory_retriever(docs):
    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=API_KEY,
        base_url=BASE_URL,
        check_embedding_ctx_length=False
    )

    vs = InMemoryVectorStore.from_documents(docs, embedding=embeddings)
    return vs.as_retriever(search_kwargs={"k": TOP_K})