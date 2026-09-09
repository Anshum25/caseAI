import os
from abc import ABC, abstractmethod
from google import genai

class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        pass
        
    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        pass

class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self):
        api_key = os.getenv("GEMINI_EMBEDDING_API_KEY")
        self.model = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    async def embed_text(self, text: str) -> list[float]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=text
        )
        return response.embeddings[0].values

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=texts
        )
        return [emb.values for emb in response.embeddings]

class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            # Uses ~80MB, extremely fast on CPU
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            raise ImportError("Please install sentence-transformers: pip install sentence-transformers")

    async def embed_text(self, text: str) -> list[float]:
        # encode returns numpy array, we convert to list of floats
        return self.model.encode(text).tolist()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
