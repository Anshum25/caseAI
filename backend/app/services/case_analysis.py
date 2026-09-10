import os
import json
from .pdf_service import pdf_service
from .providers.llm import NvidiaLLMProvider
from .providers.embeddings import LocalEmbeddingProvider
from .providers.vector_store import QdrantVectorStore

PDF_STORAGE_PATH = os.getenv("PDF_STORAGE_PATH", "./data/uploads")
PAGES_STORAGE_PATH = os.getenv("PAGES_STORAGE_PATH", "./data/pages")
STATE_STORAGE_PATH = os.getenv("STATE_STORAGE_PATH", "./data/state")

os.makedirs(PDF_STORAGE_PATH, exist_ok=True)
os.makedirs(PAGES_STORAGE_PATH, exist_ok=True)
os.makedirs(STATE_STORAGE_PATH, exist_ok=True)

class CaseAnalysisService:
    def __init__(self):
        self.llm = NvidiaLLMProvider()
        self.embeddings = LocalEmbeddingProvider()
        self.vector_store = QdrantVectorStore()
        
    def get_state_path(self, document_id: str) -> str:
        return os.path.join(STATE_STORAGE_PATH, f"{document_id}.json")

    def read_state(self, document_id: str) -> dict:
        path = self.get_state_path(document_id)
        
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"document_id": document_id, "status": "not_found"}

    def update_state(self, document_id: str, updates: dict):
        state = self.read_state(document_id)
        if state.get("status") == "not_found":
            state = {"document_id": document_id}
        state.update(updates)
        with open(self.get_state_path(document_id), "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    async def process_document_pipeline(self, document_id: str, pdf_path: str):
        try:
            import time
            t_total_start = time.perf_counter()
            self.update_state(document_id, {"status": "processing", "progress": 10})
            
            # Extract images for the frontend page viewer
            page_images_dir = os.path.join(PAGES_STORAGE_PATH, document_id)
            pdf_service.extract_pages_as_images(pdf_path, page_images_dir)
            
            # 1. Use the Hybrid Local Document Processor
            from .providers.document import HybridLocalDocumentProcessor
            print("Extracting text via Hybrid Local-First Pipeline...")
            doc_processor = HybridLocalDocumentProcessor()
            
            t_doc_extr_start = time.perf_counter()
            chunks = await doc_processor.process_pdf_to_chunks(pdf_path, document_id)
            t_doc_extr_end = time.perf_counter()
            with open("perf.log", "a") as f_log: f_log.write(f"[PERF] document extraction: {t_doc_extr_end - t_doc_extr_start:.2f}s" + "\n")
            print(f"[PERF] document extraction: {t_doc_extr_end - t_doc_extr_start:.2f}s")
            
            self.update_state(document_id, {"status": "ocr", "progress": 55, "total_pages": len(chunks)})
            
            full_text = ""
            for chunk in chunks:
                if chunk["text"].strip():
                    full_text += f"\n--- Page {chunk['page_number']} ---\n{chunk['text']}"
            
            # If still empty after all attempts, abort the pipeline
            if not full_text.strip():
                error_msg = "Error: Could not extract any text from the PDF. If this is a scanned document, OCR may have failed. Please wait and try again, or upload a clearer text-based PDF."
                self.update_state(document_id, {
                    "status": "ready",
                    "progress": 100,
                    "metadata": {},
                    "summary": error_msg
                })
                return
            
            # 3. Extract Metadata
            t_meta_start = time.perf_counter()
            metadata = await self.llm.extract_case_metadata(full_text)
            t_meta_end = time.perf_counter()
            with open("perf.log", "a") as f_log: f_log.write(f"[PERF] metadata generation: {t_meta_end - t_meta_start:.2f}s" + "\n")
            print(f"[PERF] metadata generation: {t_meta_end - t_meta_start:.2f}s")

            self.update_state(document_id, {"status": "indexing", "progress": 65})

            # 4. Create Embeddings and Store in Qdrant
            t_emb_start = time.perf_counter()
            if chunks:
                chunk_texts = [c["text"] for c in chunks]
                emb_list = await self.embeddings.embed_texts(chunk_texts)
                t_emb_end = time.perf_counter()
                with open("perf.log", "a") as f_log: f_log.write(f"[PERF] embeddings: {t_emb_end - t_emb_start:.2f}s" + "\n")
                print(f"[PERF] embeddings: {t_emb_end - t_emb_start:.2f}s")

                t_qdrant_start = time.perf_counter()
                # Ensure collection exists and has right size
                self.vector_store.init_collection(vector_size=len(emb_list[0]))
                self.vector_store.insert_chunks(document_id, chunks, emb_list)
                t_qdrant_end = time.perf_counter()
                with open("perf.log", "a") as f_log: f_log.write(f"[PERF] qdrant indexing: {t_qdrant_end - t_qdrant_start:.2f}s" + "\n")
                print(f"[PERF] qdrant indexing: {t_qdrant_end - t_qdrant_start:.2f}s")

            self.update_state(document_id, {"status": "summarizing", "progress": 85})

            # 5. Generate Case Summary
            t_summ_start = time.perf_counter()
            summary = await self.llm.generate_summary(full_text)
            t_summ_end = time.perf_counter()
            with open("perf.log", "a") as f_log: f_log.write(f"[PERF] summary generation: {t_summ_end - t_summ_start:.2f}s" + "\n")
            print(f"[PERF] summary generation: {t_summ_end - t_summ_start:.2f}s")
            
            # Save summary to state
            self.update_state(document_id, {
                "status": "ready",
                "progress": 100,
                "metadata": metadata,
                "summary": summary
            })
            
            t_total_end = time.perf_counter()
            with open("perf.log", "a") as f_log: f_log.write(f"[PERF] TOTAL: {t_total_end - t_total_start:.2f}s" + "\n")
            print(f"[PERF] TOTAL: {t_total_end - t_total_start:.2f}s")

        except Exception as e:
            print(f"Error processing document {document_id}: {e}")
            self.update_state(document_id, {"status": "failed", "error": str(e)})

case_analysis_service = CaseAnalysisService()
