import os
import json
import uuid
import datetime
from datetime import timezone
from .pdf_service import pdf_service
from .providers.llm import GroqLLMProvider
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
        self.llm = GroqLLMProvider()
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
            state = {
                "document_id": document_id,
                "created_at": datetime.datetime.now(timezone.utc).isoformat()
            }
        state.update(updates)
        with open(self.get_state_path(document_id), "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def get_history(self) -> list:
        history = []
        if not os.path.exists(STATE_STORAGE_PATH):
            return history
            
        for filename in os.listdir(STATE_STORAGE_PATH):
            if not filename.endswith(".json"):
                continue
                
            file_path = os.path.join(STATE_STORAGE_PATH, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    
                # Skip invalid states
                if not isinstance(state, dict) or "document_id" not in state:
                    continue
                    
                # Only show completed cases in history
                if state.get("status") != "ready":
                    continue
                    
                # Determine created_at (fallback to mtime if missing)
                created_at = state.get("created_at")
                if not created_at:
                    mtime = os.path.getmtime(file_path)
                    created_at = datetime.datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
                    
                # Create a lightweight record (no summary)
                record = {
                    "document_id": state.get("document_id"),
                    "filename": state.get("filename", "Unknown Document"),
                    "status": state.get("status", "unknown"),
                    "created_at": created_at,
                    "page_count": state.get("total_pages", 0),
                }
                
                # Include metadata if present
                if "metadata" in state and isinstance(state["metadata"], dict):
                    metadata = state["metadata"]
                    record.update({
                        "case_number": metadata.get("case_number"),
                        "case_type": metadata.get("case_type"),
                        "court": metadata.get("court"),
                        "petitioners": metadata.get("petitioners", []),
                        "respondents": metadata.get("respondents", []),
                        "decision_date": metadata.get("date_of_order") or metadata.get("date_of_judgment")
                    })
                    
                history.append(record)
            except Exception as e:
                print(f"Warning: Failed to read state file {filename}: {e}")
                continue
                
        # Sort descending by created_at
        history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return history

    def detect_document_language(self, text: str) -> str:
        """Detect document language using Unicode character ranges.
        Returns: 'gujarati', 'hindi', or 'english'
        """
        # Sample first 3000 chars for speed
        sample = text[:3000]
        gujarati_count = sum(1 for c in sample if '\u0A80' <= c <= '\u0AFF')
        devanagari_count = sum(1 for c in sample if '\u0900' <= c <= '\u097F')
        if gujarati_count >= 30:
            return "gujarati"
        elif devanagari_count >= 30:
            return "hindi"
        return "english"

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
            
            # 3. Extract Metadata (Compact Context: First 5 pages + Last 2 pages)
            t_meta_start = time.perf_counter()
            if len(chunks) <= 7:
                selected_chunks = chunks
            else:
                selected_chunks = chunks[:5] + chunks[-2:]
            
            metadata_text = ""
            for chunk in selected_chunks:
                if chunk["text"].strip():
                    metadata_text += f"\n--- Page {chunk['page_number']} ---\n{chunk['text']}"

            metadata = await self.llm.extract_case_metadata(metadata_text)
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

            # 5. Detect language and ask user for summary language preference
            detected_lang = self.detect_document_language(full_text)
            print(f"Detected document language: {detected_lang}")

            if detected_lang in ("gujarati", "hindi"):
                # Pause pipeline — ask user which language they want the summary in
                self.update_state(document_id, {
                    "status": "awaiting_language_choice",
                    "progress": 80,
                    "detected_language": detected_lang
                })

                # Wait up to 90 seconds for the user to choose
                import asyncio
                waited = 0
                chosen_lang = None
                while waited < 90:
                    await asyncio.sleep(1)
                    waited += 1
                    current_state = self.read_state(document_id)
                    if current_state.get("summary_language"):
                        chosen_lang = current_state["summary_language"]
                        break

                if not chosen_lang:
                    print(f"No language chosen within 90s — defaulting to English")
                    chosen_lang = "english"
            else:
                # English document — no prompt needed
                chosen_lang = "english"
                self.update_state(document_id, {"detected_language": "english"})

            self.update_state(document_id, {"status": "summarizing", "progress": 85})

            # 6. Generate Case Summary in chosen language
            t_summ_start = time.perf_counter()
            summary = await self.llm.generate_summary(full_text, language=chosen_lang)
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
