from .providers.llm import NvidiaLLMProvider
from .providers.embeddings import GeminiEmbeddingProvider, LocalEmbeddingProvider
from .providers.vector_store import QdrantVectorStore

class RetrievalService:
    def __init__(self):
        self.llm = NvidiaLLMProvider()
        self.embeddings = LocalEmbeddingProvider()
        self.vector_store = QdrantVectorStore()

    async def answer_question(self, document_id: str, question: str) -> dict:
        # 1. Embed question
        query_emb = await self.embeddings.embed_text(question)
        
        # 2. Search Qdrant
        retrieved_chunks = self.vector_store.search(document_id, query_emb, limit=12)
        
        # 3. Format Context
        context_parts = []
        citations = []
        for chunk in retrieved_chunks:
            page_num = chunk.get("page_number", "Unknown")
            text = chunk.get("text", "")
            chunk_id = chunk.get("chunk_id", "Unknown")
            context_parts.append(f"--- [Page {page_num}] [Chunk {chunk_id}] ---\n{text}")
            citations.append({
                "page": page_num,
                "chunk_id": chunk_id
            })
            
        context_str = "\n\n".join(context_parts)
        
        # 4. Generate Answer
        answer = await self.llm.answer_question(question, context_str)
        
        # We assume the LLM outputs citations as `[p. X]`. We provide the full chunks array so frontend can link them.
        return {
            "answer": answer,
            "citations": citations
        }

retrieval_service = RetrievalService()
