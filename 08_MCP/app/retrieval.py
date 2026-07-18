import os

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

from .server import oauth_provider

COLLECTION_NAME = "catshop_products"
EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
TOP_K = 5

_vector_store: QdrantVectorStore | None = None
_embeddings: OpenAIEmbeddings | None = None


def _get_embeddings() -> OpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    return _embeddings


async def _build_vector_store() -> QdrantVectorStore:
    embeddings = _get_embeddings()
    db = await oauth_provider._get_db()
    cursor = await db.execute(
        "SELECT id, name, description, price, category FROM products"
    )
    rows = await cursor.fetchall()

    documents = []
    for row in rows:
        product_id, name, description, price, category = row
        page_content = f"{name}\n{description}\nCategory: {category}"
        documents.append(
            Document(
                page_content=page_content,
                metadata={
                    "id": product_id,
                    "name": name,
                    "description": description,
                    "price": price,
                    "category": category,
                },
            )
        )

    return QdrantVectorStore.from_documents(
        documents=documents,
        embedding=embeddings,
        location=":memory:",
        collection_name=COLLECTION_NAME,
        force_recreate=True,
    )


async def get_vector_store() -> QdrantVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = await _build_vector_store()
    return _vector_store


async def search_products(query: str, k: int = TOP_K) -> list[dict]:
    if not query or not query.strip():
        raise ValueError("Query must be a non-empty string")

    vector_store = await get_vector_store()
    results = vector_store.similarity_search_with_score(query, k=k)

    return [
        {
            "id": doc.metadata["id"],
            "name": doc.metadata["name"],
            "description": doc.metadata["description"],
            "price": doc.metadata["price"],
            "category": doc.metadata["category"],
            "score": round(float(score), 4),
        }
        for doc, score in results
    ]
