import os
import uuid
from abc import ABC, abstractmethod
from qdrant_client import QdrantClient
from qdrant_client.http import models

class VectorStore(ABC):
    @abstractmethod
    def init_collection(self, vector_size: int):
        pass
        
    @abstractmethod
    def insert_chunks(self, document_id: str, chunks: list[dict], embeddings: list[list[float]]):
        pass
        
    @abstractmethod
    def search(self, document_id: str, query_embedding: list[float], limit: int = 10) -> list[dict]:
        pass

_qdrant_client_instance = None

class QdrantVectorStore(VectorStore):
    def __init__(self):
        global _qdrant_client_instance
        qdrant_url = "local" # Forced to local to bypass .env caching issue
        qdrant_api_key = os.getenv("QDRANT_API_KEY", "")
        self.collection_name = os.getenv("QDRANT_COLLECTION", "legal_case_chunks")
        
        if _qdrant_client_instance is None:
            if qdrant_url.lower() == "local":
                # Uses local file system instead of requiring Docker
                _qdrant_client_instance = QdrantClient(path="qdrant_storage")
            else:
                _qdrant_client_instance = QdrantClient(
                    url=qdrant_url,
                    api_key=qdrant_api_key if qdrant_api_key else None
                )
        self.client = _qdrant_client_instance

    def init_collection(self, vector_size: int):
        try:
            if self.client.collection_exists(self.collection_name):
                # Check if existing collection has the right vector size
                info = self.client.get_collection(self.collection_name)
                existing_size = info.config.params.vectors.size
                if existing_size != vector_size:
                    print(f"Vector size mismatch: existing={existing_size}, new={vector_size}. Recreating collection...")
                    self.client.delete_collection(self.collection_name)
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=models.VectorParams(
                            size=vector_size,
                            distance=models.Distance.COSINE
                        )
                    )
                    print(f"Recreated Qdrant collection: {self.collection_name} with size={vector_size}")
            else:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    )
                )
                print(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            print(f"Error initializing Qdrant collection: {e}")

    def insert_chunks(self, document_id: str, chunks: list[dict], embeddings: list[list[float]]):
        points = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            payload = {
                "document_id": document_id,
                "page_number": chunk.get("page_number"),
                "page_numbers": chunk.get("page_numbers", [chunk.get("page_number")]),
                "chunk_id": f"{document_id}-page{chunk.get('page_number')}-{i}",
                "chunk_index": i,
                "text": chunk.get("text"),
                "language": chunk.get("language", "auto"),
                "section": chunk.get("section", "general"),
                "document_type": chunk.get("document_type", "unknown"),
                "source": "gemini"
            }
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=emb,
                    payload=payload
                )
            )
        
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

    def search(self, document_id: str, query_embedding: list[float], limit: int = 15) -> list[dict]:
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=limit
            )
            return [hit.payload for hit in results.points]
        except Exception as e:
            print(f"Search failed: {e}")
            return []
