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

async def run_benchmark():
    doc_id = "groq_perf_benchmark_001"
    src_pdf = "data/uploads/ea6b6a07-6dc7-4ed2-b127-448f88bb600d.pdf"
    dest_pdf = f"data/uploads/{doc_id}.pdf"
    
    print("=== STARTING GROQ MIGRATION BENCHMARK ===")
    with open(dest_pdf, "wb") as buffer:
        with open(src_pdf, "rb") as f:
            shutil.copyfileobj(f, buffer)
            
    print("Running document processing pipeline...")
    await case_analysis_service.process_document_pipeline(doc_id, dest_pdf)
    
    print("\nRunning chat retrieval test...")
    chat_result = await retrieval_service.answer_question(doc_id, "What is the outcome of the appeal?")
    print("Chat Answer Snippet:", chat_result["answer"][:300])
    print("Citations:", chat_result["citations"])
    print("=== BENCHMARK COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
