import os
from pinecone import Pinecone

api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME", "axiom")

pc = None
vector_store = None

if api_key:
    pc = Pinecone(api_key=api_key)
    try:
        vector_store = pc.Index(index_name)
    except Exception as e:
        print(f"Error connecting to Pinecone Index: {e}")

def store_embedding(asset_id: str, embedding: list[float]):
    if not vector_store:
        return
    vector_store.upsert(
        vectors=[
            {"id": asset_id, "values": embedding}
        ]
    )

def search_nearest_assets(embedding: list[float], top_k: int = 5):
    if not vector_store:
        return []
    result = vector_store.query(
        vector=embedding,
        top_k=top_k,
        include_values=False
    )
    matches = result.get('matches', [])
    # Serialize to prevent FastAPI RecursionError on Pinecone object representation
    return [{"id": getattr(m, "id", str(m)), "score": getattr(m, "score", 0.0)} for m in matches]
