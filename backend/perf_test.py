import sys
import os
import asyncio
import time
import shutil

sys.path.append(os.getcwd())
from dotenv import load_dotenv
load_dotenv()

from app.services.case_analysis import case_analysis_service
from app.services.retrieval import retrieval_service

async def run_test():
    doc_id = "test_perf_doc_123"
    src_pdf = "data/uploads/ea6b6a07-6dc7-4ed2-b127-448f88bb600d.pdf"
    dest_pdf = f"data/uploads/{doc_id}.pdf"
    
    print("--- STARTING UPLOAD TEST ---")
    t_up_start = time.perf_counter()
    with open(dest_pdf, "wb") as buffer:
        with open(src_pdf, "rb") as f:
            shutil.copyfileobj(f, buffer)
    t_up_end = time.perf_counter()
    print(f"[PERF] upload/save: {t_up_end - t_up_start:.2f}s")
    
    print("--- STARTING PIPELINE TEST ---")
    await case_analysis_service.process_document_pipeline(doc_id, dest_pdf)
    print("--- FINISHED PIPELINE TEST ---")
    
    print("--- STARTING CHAT TEST ---")
    await retrieval_service.answer_question(doc_id, "What is the reference number in this document?")
    print("--- FINISHED CHAT TEST ---")

if __name__ == "__main__":
    asyncio.run(run_test())
