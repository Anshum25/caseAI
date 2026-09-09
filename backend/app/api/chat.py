from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..services.case_analysis import case_analysis_service
from ..services.retrieval import retrieval_service

router = APIRouter()

class ChatRequest(BaseModel):
    question: str

@router.post("/{document_id}/chat")
async def chat_with_document(document_id: str, request: ChatRequest):
    state = case_analysis_service.read_state(document_id)
    if state.get("status") != "ready":
        raise HTTPException(status_code=400, detail="Document is not ready yet")
        
    try:
        response = await retrieval_service.answer_question(document_id, request.question)
        
        return {
            "answer": response["answer"],
            "language": "auto",  # The LLM automatically responds in the prompt's language
            "citations": response["citations"]
        }
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Error generating answer")
