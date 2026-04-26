import os
from pathlib import Path
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

def store_embedding(asset_id: str, embedding: list):
    if not vector_store:
        return
    try:
        vector_store.upsert(
            vectors=[
                {"id": asset_id, "values": embedding}
            ]
        )
    except Exception as e:
        print(f"⚠ Error storing embedding: {e}")

def search_nearest_assets(embedding: list, top_k: int = 5):
    if not vector_store:
        return []
    try:
        result = vector_store.query(
            vector=embedding,
            top_k=top_k,
            include_values=False
        )
        matches = result.get('matches', [])
        # Serialize to prevent FastAPI RecursionError on Pinecone object representation
        return [{"id": getattr(m, "id", str(m)), "score": getattr(m, "score", 0.0)} for m in matches]
    except Exception as e:
        print(f"⚠ Error searching vectors: {e}")
        return []
