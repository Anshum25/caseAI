from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import documents, chat, health
from .services.providers.vector_store import QdrantVectorStore

app = FastAPI(title="NyayaAI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Initializing NyayaAI Backend...")
    try:
        # Initialize Qdrant collection (Defaulting to 768 for text-embedding-004)
        vs = QdrantVectorStore()
        vs.init_collection(vector_size=768)
        print("Qdrant connected. Collection ready.")
    except Exception as e:
        print(f"Warning: Could not initialize Qdrant on startup. {e}")

# Include routers
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/documents", tags=["chat"])
app.include_router(health.router, prefix="/api", tags=["health"])

@app.get("/")
async def root():
    return {"message": "NyayaAI API is running"}
