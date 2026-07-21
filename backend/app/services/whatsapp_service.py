import httpx
import json
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from ..core.config import settings
from ..db.models import Conversation, Lead, MessageLog
from datetime import datetime

class WhatsAppService:
    def __init__(self):
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.base_url = "https://graph.facebook.com/v20.0"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def send_message(self, to: str, message: str, message_id: Optional[str] = None) -> Dict:
        """Send text message via WhatsApp Cloud API"""
        if not self.access_token or not self.phone_number_id:
            print("⚠️  WhatsApp credentials missing. Simulating send.")
            return {"status": "simulated", "to": to, "message": message[:100]}

        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }

        try:
            resp = await self.client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"WhatsApp send error: {e}")
            return {"error": str(e)}

    async def send_template_message(self, to: str, template_name: str, params: List[str]):
        """Send a template message (e.g. appointment confirmation)"""
        # Implement if needed for production
        pass

    async def get_conversation_context(self, whatsapp_id: str, limit: int = 5) -> List[Dict]:
        """Fetch recent conversation history (for context memory)"""
        # In prod: use Redis. Here: placeholder
        return []

    async def log_conversation(
        self, 
        db: Session, 
        whatsapp_id: str, 
        incoming: str, 
        outgoing: str, 
        intent: str, 
        sentiment: str
    ):
        """Persist conversation"""
        log = MessageLog(
            whatsapp_id=whatsapp_id,
            direction="in",
            message=incoming,
            message_type="text",
            timestamp=datetime.utcnow()
        )
        db.add(log)

        conv = Conversation(
            whatsapp_id=whatsapp_id,
            message=incoming,
            response=outgoing,
            intent=intent,
            sentiment=sentiment,
            metadata={"source": "whatsapp"}
        )
        db.add(conv)
        db.commit()

    async def log_lead_from_stock(self, db: Session, whatsapp_id: str, stock_results: List[Dict]):
        """Auto-create or update lead when stock is queried"""
        if not stock_results:
            return

        lead = db.query(Lead).filter(Lead.whatsapp_id == whatsapp_id).first()
        if not lead:
            lead = Lead(
                name=f"WhatsApp User {whatsapp_id[-6:]}",
                phone=whatsapp_id,
                whatsapp_id=whatsapp_id,
                status="new",
                interest="diamond stock query",
                rep_no=str(stock_results[0].get("rep_no")),
                stone_no=str(stock_results[0].get("stone_no")),
                score=75.0,
            )
            db.add(lead)
        else:
            if stock_results[0].get("rep_no"):
                lead.rep_no = str(stock_results[0].get("rep_no"))
                lead.stone_no = str(stock_results[0].get("stone_no"))
                lead.score = max(lead.score or 0, 70.0)
        db.commit()

    async def send_stock_reply(self, to: str, stock_response: str):
        """Convenience method"""
        await self.send_message(to, stock_response)
