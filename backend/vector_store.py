import os
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
env_path = Path('.env')
if not env_path.exists():
    env_path = Path('../.env')
load_dotenv(dotenv_path=env_path)

try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    print("⚠ Pinecone not available, vector operations will be disabled")
    PINECONE_AVAILABLE = False
    Pinecone = None

api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME", "axiom")

pc = None
vector_store = None

if PINECONE_AVAILABLE and api_key:
    try:
        pc = Pinecone(api_key=api_key)
        vector_store = pc.Index(index_name)
        print("✓ Connected to Pinecone vector store")
    except Exception as e:
        print(f"⚠ Error connecting to Pinecone Index: {e}")
else:
    print("⚠ Pinecone not configured, vector operations will be disabled")


def store_embedding(asset_id: str, embedding: List[float]):
    """Bare upsert — no metadata. Kept for backward compatibility."""
    if not vector_store:
        return
    try:
        vector_store.upsert(vectors=[{"id": asset_id, "values": embedding}])
    except Exception as e:
        print(f"⚠ Error storing embedding: {e}")


def store_embedding_with_metadata(
    asset_id: str,
    embedding: List[float],
    metadata: Optional[Dict] = None,
):
    """
    Upserts an embedding into Pinecone with optional metadata for filtered search.

    Args:
        asset_id:  Pinecone vector ID.
        embedding: 1408-dimensional float vector.
        metadata:  Dict with classification, confidence, platform, etc.
    """
    if not vector_store:
        return
    try:
        vector_store.upsert(
            vectors=[{
                "id": asset_id,
                "values": embedding,
                "metadata": metadata or {},
            }]
        )
    except Exception as e:
        print(f"⚠ Error storing embedding with metadata: {e}")


def search_nearest_assets(
    embedding: List[float],
    top_k: int = 5,
    filter_metadata: Optional[Dict] = None,
) -> List[Dict]:
    """
    Queries Pinecone for the nearest asset vectors.

    Args:
        embedding:       Query vector (1408 dims).
        top_k:           Number of results to return.
        filter_metadata: Optional Pinecone metadata filter dict.

    Returns:
        List of {"id": str, "score": float} dicts.
    """
    if not vector_store:
        return []
    try:
        query_kwargs = {
            "vector": embedding,
            "top_k": top_k,
            "include_values": False,
            "include_metadata": True,
        }
        if filter_metadata:
            query_kwargs["filter"] = filter_metadata

        result = vector_store.query(**query_kwargs)
        matches = result.get("matches", [])
        return [
            {
                "id": getattr(m, "id", str(m)),
                "score": getattr(m, "score", 0.0),
                "metadata": getattr(m, "metadata", {}),
            }
            for m in matches
        ]
    except Exception as e:
        print(f"⚠ Error searching vectors: {e}")
        return []
