import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ..services.case_analysis import case_analysis_service, PDF_STORAGE_PATH, PAGES_STORAGE_PATH

router = APIRouter()

class LanguageChoice(BaseModel):
    language: str  # "gujarati" | "hindi" | "english"

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    document_id = str(uuid.uuid4())
    file_path = os.path.join(PDF_STORAGE_PATH, f"{document_id}.pdf")
    
    import time
    t_up_start = time.perf_counter()
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    t_up_end = time.perf_counter()
    print(f"[PERF] upload/save: {t_up_end - t_up_start:.2f}s")
        
    # Initialize state
    case_analysis_service.update_state(document_id, {
        "status": "uploading", 
        "progress": 0,
        "filename": file.filename
    })
    
    # Start background processing
    background_tasks.add_task(case_analysis_service.process_document_pipeline, document_id, file_path)
    
    return {"document_id": document_id, "status": "processing"}

@router.get("/history")
async def get_history():
    history = case_analysis_service.get_history()
    return {"history": history}

@router.get("/{document_id}")
async def get_document(document_id: str):
    # Prevent path traversal by ensuring it's a valid UUID
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    state = case_analysis_service.read_state(document_id)
    if state.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Document not found")
        
    return {
        "document_id": state.get("document_id"),
        "filename": state.get("filename"),
        "status": state.get("status"),
        "created_at": state.get("created_at"),
        "page_count": state.get("total_pages", 0),
        "metadata": state.get("metadata", {}),
        "summary": state.get("summary", ""),
        "progress": state.get("progress", 0),
        "detected_language": state.get("detected_language")
    }

@router.post("/{document_id}/language")
async def set_document_language(document_id: str, body: LanguageChoice):
    """Set the user's preferred summary language. The pipeline waits on this."""
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    state = case_analysis_service.read_state(document_id)
    if state.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Document not found")

    allowed = {"gujarati", "hindi", "english"}
    lang = body.language.lower().strip()
    if lang not in allowed:
        raise HTTPException(status_code=400, detail=f"Language must be one of: {allowed}")

    case_analysis_service.update_state(document_id, {"summary_language": lang})
    return {"document_id": document_id, "summary_language": lang}

@router.get("/{document_id}/status")
async def get_document_status(document_id: str):
    state = case_analysis_service.read_state(document_id)
    if state.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Document not found")
        
    return {
        "document_id": state.get("document_id"), 
        "status": state.get("status"), 
        "progress": state.get("progress", 0),
        "stage": state.get("status")
    }

@router.get("/{document_id}/summary")
async def get_document_summary(document_id: str):
    state = case_analysis_service.read_state(document_id)
    if state.get("status") != "ready":
        raise HTTPException(status_code=400, detail="Document is not ready yet")
        
    return {
        "document_id": document_id,
        "summary": state.get("summary", {}),
        "metadata": state.get("metadata", {})
    }

@router.get("/{document_id}/pages/{page_number}")
async def get_document_page_image(document_id: str, page_number: int):
    image_path = os.path.join(PAGES_STORAGE_PATH, document_id, f"page_{page_number}.png")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Page image not found")
    return FileResponse(image_path)
