import os, re
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

load_dotenv()
ZWNJ = "‌"
ROLES = ["manager", "staff", "teacher", "counselor", "parent", "student"]

def normalize(t: str) -> str:
    # Same normalization for documents and questions, otherwise search breaks
    t = t.replace("­", "").replace("ي", "ی").replace("ك", "ک")
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()

embed_client = OpenAI(base_url=os.getenv("EMBED_BASE_URL"), api_key=os.getenv("EMBED_API_KEY"))
EMBED_MODEL = os.getenv("EMBED_MODEL")

def embed(texts):
    r = embed_client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in r.data]

def collection():
    db = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "./db"))
    return db.get_or_create_collection("docs", metadata={"hnsw:space": "cosine"})
