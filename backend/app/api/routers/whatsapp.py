from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
import json
from typing import Optional
from collections import defaultdict
from datetime import datetime, timedelta
from ...core.config import settings
from ...services.whatsapp_service import WhatsAppService
from ...services.ai_service import AIService
from ...db.session import get_db
from sqlalchemy.orm import Session

# Simple in-memory rate limiting
user_message_times = defaultdict(list)  # whatsapp_id -> list of timestamps
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10     # messages per window per user

router = APIRouter()
whatsapp_service = WhatsAppService()
ai_service = AIService()

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    """Meta WhatsApp Cloud API verification endpoint."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        print("✅ WhatsApp webhook verified successfully!")
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/webhook")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming WhatsApp messages and auto-reply."""
    try:
        data = await request.json()
        print(f"📩 Webhook received: {json.dumps(data)[:300]}...")

        # Extract message
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "ok"}

        msg = messages[0]
        wa_id = msg.get("from")
        msg_id = msg.get("id")
        msg_type = msg.get("type", "text")

        # Extract content
        text_body = ""
        media_info = None

        if msg_type == "text":
            text_body = msg.get("text", {}).get("body", "")
        elif msg_type == "image":
            text_body = "User sent an image"
            media_info = {"type": "image", "id": msg.get("image", {}).get("id")}
        elif msg_type == "audio":
            text_body = "User sent a voice note"
            media_info = {"type": "audio", "id": msg.get("audio", {}).get("id")}
        elif msg_type == "document":
            text_body = "User sent a document"
            media_info = {"type": "document"}

        # === BASIC RATE LIMITING PER USER ===
        now = datetime.utcnow()
        user_times = user_message_times[wa_id]
        # Keep only recent timestamps
        user_times[:] = [t for t in user_times if (now - t).total_seconds() < RATE_LIMIT_WINDOW]
        
        if len(user_times) >= RATE_LIMIT_MAX:
            await whatsapp_service.send_message(to=wa_id, message="You're sending messages too quickly. Please wait a moment.")
            return {"status": "rate_limited"}
        
        user_times.append(now)

        # === HUMAN HANDOVER SUPPORT ===
        if "human" in text_body.lower() or "speak to" in text_body.lower() or "agent" in text_body.lower():
            reply_text = "Thank you. A human agent will contact you shortly. Meanwhile, you can continue chatting with me."
            await whatsapp_service.send_message(to=wa_id, message=reply_text)
            await whatsapp_service.log_conversation(db, wa_id, text_body, reply_text, "human_handover", "neutral")
            return {"status": "human_handover"}

        # Get conversation context
        context = await whatsapp_service.get_conversation_context(wa_id)

        # Generate AI response (trained Q&A + stock)
        ai_response = await ai_service.generate_response(
            message=text_body,
            whatsapp_id=wa_id,
            context=context,
            media_info=media_info
        )

        # Send reply
        await whatsapp_service.send_message(
            to=wa_id,
            message=ai_response["response"],
            message_id=msg_id
        )

        # Log + increment stats
        await whatsapp_service.log_conversation(
            db=db,
            whatsapp_id=wa_id,
            incoming=text_body,
            outgoing=ai_response["response"],
            intent=ai_response["intent"],
            sentiment=ai_response.get("sentiment", "neutral")
        )

        # Simple daily counter (in-memory, for demo)
        from app.api.routers.stats import increment_message
        increment_message(wa_id)

        if ai_response.get("stock_results"):
            await whatsapp_service.log_lead_from_stock(db, wa_id, ai_response["stock_results"])

        return {"status": "success"}

    except Exception as e:
        print(f"❌ Webhook error: {str(e)}")
        # Still acknowledge to avoid Meta retries
        return {"status": "error_handled", "detail": str(e)}

@router.post("/send")
async def send_manual_message(
    to: str,
    message: str,
    db: Session = Depends(get_db)
):
    """Manual send (used by dashboard)"""
    result = await whatsapp_service.send_message(to=to, message=message)
    return {"status": "sent", "result": result}

@router.post("/broadcast")
async def broadcast_message(
    message: str,
    phone_numbers: list[str],
    db: Session = Depends(get_db)
):
    """Broadcast to multiple leads (use carefully)"""
    results = []
    for phone in phone_numbers[:50]:  # safety limit
        res = await whatsapp_service.send_message(to=phone, message=message)
        results.append({"to": phone, "status": "sent"})
    return {"broadcasted": len(results), "results": results}
