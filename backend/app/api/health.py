import os
from fastapi import APIRouter
from ..services.providers.vector_store import QdrantVectorStore

router = APIRouter()

@router.get("/health")
async def health_check():
    health_status = {
        "backend": "ok",
        "gemini": "unknown",
        "qdrant": "unknown"
    }
    
    # Check Gemini config
    llm_key = os.getenv("GEMINI_LLM_API_KEY")
    emb_key = os.getenv("GEMINI_EMBEDDING_API_KEY")
    if llm_key and emb_key:
        health_status["gemini"] = "ok"
    else:
        health_status["gemini"] = "missing_keys"
        
    # Check Qdrant connectivity
    try:
        vs = QdrantVectorStore()
        # A simple check to see if we can talk to Qdrant
        collections = vs.client.get_collections()
        health_status["qdrant"] = "ok"
    except Exception as e:
        health_status["qdrant"] = "error"
        
    return health_status
