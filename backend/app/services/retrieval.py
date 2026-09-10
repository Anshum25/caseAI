from .providers.llm import NvidiaLLMProvider
from .providers.embeddings import GeminiEmbeddingProvider, LocalEmbeddingProvider
from .providers.vector_store import QdrantVectorStore

class RetrievalService:
    def __init__(self):
        self.llm = NvidiaLLMProvider()
        self.embeddings = LocalEmbeddingProvider()
        self.vector_store = QdrantVectorStore()

    async def answer_question(self, document_id: str, question: str) -> dict:
        import time
        t_chat_start = time.perf_counter()
        
        # 1. Embed question
        t_qemb_start = time.perf_counter()
        query_emb = await self.embeddings.embed_text(question)
        t_qemb_end = time.perf_counter()
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF CHAT] query embedding: {t_qemb_end - t_qemb_start:.2f}s" + "\n")
        print(f"[PERF CHAT] query embedding: {t_qemb_end - t_qemb_start:.2f}s")
        
        # 2. Search Qdrant
        t_qsearch_start = time.perf_counter()
        retrieved_chunks = self.vector_store.search(document_id, query_emb, limit=12)
        t_qsearch_end = time.perf_counter()
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF CHAT] qdrant search: {t_qsearch_end - t_qsearch_start:.2f}s" + "\n")
        print(f"[PERF CHAT] qdrant search: {t_qsearch_end - t_qsearch_start:.2f}s")
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF CHAT] retrieved chunks: {len(retrieved_chunks)}" + "\n")
        print(f"[PERF CHAT] retrieved chunks: {len(retrieved_chunks)}")
        
        # 3. Format Context
        t_fmt_start = time.perf_counter()
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
        t_fmt_end = time.perf_counter()
        
        chars = len(context_str)
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF CHAT] context chars: {chars}" + "\n")
        print(f"[PERF CHAT] context chars: {chars}")
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF CHAT] estimated context tokens: {chars // 4}" + "\n")
        print(f"[PERF CHAT] estimated context tokens: {chars // 4}")
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF CHAT] prompt construction: {t_fmt_end - t_fmt_start:.2f}s" + "\n")
        print(f"[PERF CHAT] prompt construction: {t_fmt_end - t_fmt_start:.2f}s")
        
        # 4. Generate Answer
        t_llm_start = time.perf_counter()
        answer = await self.llm.answer_question(question, context_str)
        t_llm_end = time.perf_counter()
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF CHAT] groq request: {t_llm_end - t_llm_start:.2f}s" + "\n")
        print(f"[PERF CHAT] groq request: {t_llm_end - t_llm_start:.2f}s")
        
        t_parse_start = time.perf_counter()
        import re
        cited_pages = set()
        # Extract page numbers from formats like [p. 32], page 32, p. 32, [32]
        matches = re.findall(r'(?:page|p\.|\[)\s*(\d+)', answer, re.IGNORECASE)
        for m in matches:
            cited_pages.add(int(m))
            
        filtered_citations = []
        seen_pages = set()
        
        for c in citations:
            page_val = c.get("page")
            if isinstance(page_val, (int, str)) and str(page_val).isdigit():
                page_int = int(page_val)
                if page_int in cited_pages and page_int not in seen_pages:
                    filtered_citations.append(c)
                    seen_pages.add(page_int)
        t_parse_end = time.perf_counter()
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF CHAT] response parsing: {t_parse_end - t_parse_start:.2f}s" + "\n")
        print(f"[PERF CHAT] response parsing: {t_parse_end - t_parse_start:.2f}s")
        
        t_chat_end = time.perf_counter()
        with open("perf.log", "a") as f_log: f_log.write(f"[PERF CHAT] TOTAL: {t_chat_end - t_chat_start:.2f}s" + "\n")
        print(f"[PERF CHAT] TOTAL: {t_chat_end - t_chat_start:.2f}s")
        
        # If no citations were extracted but we retrieved chunks, we can either return empty or a limited set.
        # Returning empty is more accurate to what was actually cited.
        
        return {
            "answer": answer,
            "citations": filtered_citations
        }

retrieval_service = RetrievalService()
