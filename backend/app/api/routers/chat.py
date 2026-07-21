from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...models.schemas import ChatRequest, ChatResponse
from ...services.ai_service import AIService
from ...db.session import get_db

router = APIRouter()
ai_service = AIService()

@router.post("/", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """REST API endpoint for direct chat (dashboard + testing)"""
    response = await ai_service.generate_response(
        message=request.message,
        whatsapp_id=request.whatsapp_id,
        context=None,
        media_info={"type": request.media_type} if request.media_url else None
    )
    return ChatResponse(**response)
