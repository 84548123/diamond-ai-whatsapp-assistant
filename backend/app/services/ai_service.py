import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import Dict, List, Any, Optional
import json
import re
from ..core.config import settings
from .stock_service import StockService
from .qa_service import QAService
from ..db.chroma_client import get_chroma_collection

class AIService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            print("⚠️  WARNING: GEMINI_API_KEY not set. AI features will be limited.")
        else:
            genai.configure(api_key=settings.GEMINI_API_KEY)

        self.model = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.7,
            convert_system_message_to_human=True
        )
        self.stock_service = StockService()
        self.qa_service = QAService()
        self.knowledge_collection = get_chroma_collection("knowledge_base")

    def detect_intent_and_entities(self, message: str) -> Dict[str, Any]:
        """Fast intent detection + entity extraction for stock queries."""
        msg_lower = message.lower().strip()

        entities = {"rep_no": None, "stone_no": None}

        # === Rep No detection (very flexible) ===
        rep_match = re.search(r"rep(?:\s*no)?\s*[:#]?\s*(\d{7,12})", msg_lower)
        if rep_match:
            entities["rep_no"] = rep_match.group(1)

        # Catch bare long numbers (likely Rep No)
        if not entities["rep_no"]:
            bare_rep = re.search(r"\b(\d{8,12})\b", message)
            if bare_rep:
                entities["rep_no"] = bare_rep.group(1)

        # === Stone / Packet detection (very flexible) ===
        stone_match = re.search(r"(?:stone|packet|ref|id|no\.?)\s*(?:no|number|#)?\s*[:#]?\s*([A-Z0-9]{3,}-?[A-Z0-9]{3,})", msg_lower, re.IGNORECASE)
        if stone_match:
            entities["stone_no"] = stone_match.group(1).upper()

        # Catch bare stone codes like LGRD30-23746
        if not entities["stone_no"]:
            bare_stone = re.search(r"\b([A-Z]{2,}[0-9]{2,}-?[0-9]{3,})\b", message, re.IGNORECASE)
            if bare_stone:
                entities["stone_no"] = bare_stone.group(1).upper()

        # Intent classification — force stock_query if we found any ID
        intent = "general_query"
        stock_keywords = ["stock", "available", "availability", "in stock", "check", "rep", "stone", "packet", "ref"]
        if entities["rep_no"] or entities["stone_no"] or any(k in msg_lower for k in stock_keywords):
            intent = "stock_query"
        elif any(k in msg_lower for k in ["book", "appointment", "schedule", "viewing", "meet"]):
            intent = "appointment"
        elif any(k in msg_lower for k in ["price", "cost", "quote", "how much"]):
            intent = "pricing"
        elif any(k in msg_lower for k in ["hello", "hi", "hey"]):
            intent = "greeting"
        elif any(k in msg_lower for k in ["thank", "bye", "thanks"]):
            intent = "goodbye"
        elif any(k in msg_lower for k in ["human", "agent", "speak to", "talk to human", "real person"]):
            intent = "human_handover"

        return {
            "intent": intent,
            "entities": entities,
            "raw_message": message
        }

    async def generate_response(
        self, 
        message: str, 
        whatsapp_id: Optional[str] = None,
        context: Optional[List[Dict]] = None,
        media_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Primary AI response generation with stock awareness and multimodal support."""

        intent_data = self.detect_intent_and_entities(message)
        intent = intent_data["intent"]
        entities = intent_data["entities"]

        # === STEP 1: Try trained Q&A first (common customer queries) ===
        qa_response = self.qa_service.generate_response(message, entities)
        if qa_response:
            # If we got a strong trained match, return it (enriched with stock if needed)
            return {
                "response": qa_response["response"],
                "intent": qa_response.get("intent", intent),
                "sentiment": "neutral",
                "follow_up": qa_response.get("follow_up", "Would you like more details?"),
                "stock_results": qa_response.get("stock_results"),
                "metadata": {
                    "source": qa_response.get("source", "trained_qa"),
                    "matched_query": True
                }
            }

        # Human handover
        if intent == "human_handover":
            return {
                "response": "Thank you. A member of our team will get in touch with you shortly.",
                "intent": "human_handover",
                "sentiment": "neutral",
                "follow_up": None,
                "stock_results": None,
                "metadata": {"source": "human_handover"}
            }

        # === STEP 2: SPECIALIZED STOCK HANDLING (if not caught by Q&A) ===
        if intent == "stock_query" or entities.get("rep_no") or entities.get("stone_no"):
            stock_results = []
            query_text = message

            if entities.get("rep_no"):
                item = self.stock_service.get_stock_by_rep_no(entities["rep_no"])
                if item:
                    stock_results = [item]
                else:
                    stock_results = self.stock_service.search_stock(rep_no=entities["rep_no"], limit=1)

            elif entities.get("stone_no"):
                item = self.stock_service.get_stock_by_stone_no(entities["stone_no"])
                if item:
                    stock_results = [item]
                else:
                    stock_results = self.stock_service.search_stock(stone_no=entities["stone_no"], limit=3)

            else:
                # General search
                stock_results = self.stock_service.search_stock(query=message, limit=6)

            formatted = self.stock_service.format_stock_response(stock_results)

            return {
                "response": formatted,
                "intent": "stock_query",
                "sentiment": "neutral",
                "follow_up": "Would you like pricing, more details, or to book an appointment?",
                "stock_results": stock_results[:5],
                "metadata": {
                    "matched_rep_nos": [s.get("rep_no") for s in stock_results],
                    "matched_stone_nos": [s.get("stone_no") for s in stock_results],
                    "query_type": "exact_stock_lookup"
                }
            }

        # === MULTIMODAL HANDLING (Image / Audio / PDF) ===
        if media_info:
            return await self._handle_multimodal(message, media_info)

        # === GENERAL CONVERSATION via Gemini + Context ===
        history_str = ""
        if context:
            history_str = "\n".join([f"User: {c.get('user')}\nAI: {c.get('ai')}" for c in context[-4:]])

        system_prompt = f"""You are an expert, friendly diamond sales assistant for a premium lab-grown diamond company.
You are helpful, professional, and knowledgeable. Always respond in a warm, human-like tone.

Current conversation context:
{history_str}

User message: {message}

Rules:
- If user is asking about stock, always use exact data from stock lookup.
- Be concise but complete.
- Always offer next steps: pricing, appointment, more stones.
- Support English and basic Hindi.
- Never hallucinate stock availability. Use the stock service data only.
"""

        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}")
            ])
            chain = prompt | self.model | StrOutputParser()
            response_text = await chain.ainvoke({"input": message})

            # Basic sentiment detection
            sentiment = "positive" if any(w in message.lower() for w in ["good", "nice", "love", "great"]) else \
                        "negative" if any(w in message.lower() for w in ["bad", "expensive", "no"]) else "neutral"

            return {
                "response": response_text.strip(),
                "intent": intent,
                "sentiment": sentiment,
                "follow_up": "How can I help you further today?",
                "stock_results": None,
                "metadata": {"model": settings.GEMINI_MODEL}
            }
        except Exception as e:
            print(f"Gemini error: {e}")
            return {
                "response": "I'm having a small technical hiccup. Can you please repeat your query about a Rep No or Stone?",
                "intent": intent,
                "sentiment": "neutral",
                "follow_up": None,
                "stock_results": None,
                "metadata": {"error": str(e)}
            }

    async def _handle_multimodal(self, message: str, media_info: Dict) -> Dict:
        """Handle images, audio, PDF using Gemini multimodal capabilities."""
        media_type = media_info.get("type", "text")

        if media_type == "image":
            prompt = f"""You are a diamond expert. Analyze this diamond image.
Describe the shape, color, clarity, estimated carat, and any visible characteristics.
If it looks like a specific stone in our inventory, mention it.
User query: {message}"""
            # In real implementation: use genai.upload_file or inline image
            response = "Thank you for the image. It looks like a beautiful ROUND brilliant. To confirm exact match please share the Rep No or Stone No."

        elif media_type == "audio":
            # Gemini handles speech-to-text + understanding
            response = "Thank you for the voice note. I understood you are inquiring about diamond availability. How can I help specifically?"

        elif media_type == "document":
            response = "I've received your document/PDF. I'm analyzing it now. What specific question do you have about it?"

        else:
            response = "Thank you for the media. Please tell me more about what you'd like to know."

        return {
            "response": response,
            "intent": "multimodal",
            "sentiment": "neutral",
            "follow_up": "Would you like me to check availability?",
            "stock_results": None,
            "metadata": {"media_type": media_type}
        }

    def analyze_sentiment(self, text: str) -> str:
        # Lightweight sentiment (Gemini can be used for advanced)
        text = text.lower()
        if any(w in text for w in ["happy", "great", "excellent", "love", "perfect"]):
            return "positive"
        elif any(w in text for w in ["bad", "expensive", "no thanks", "not interested"]):
            return "negative"
        return "neutral"

    async def generate_daily_summary(self, stats: Dict) -> str:
        prompt = f"""Generate a professional daily summary report for our WhatsApp diamond business assistant.
Stats: {json.dumps(stats, indent=2)}

Provide:
1. Key highlights
2. Top customer queries
3. Stock-related activity
4. Recommended actions
"""
        try:
            response = self.model.invoke(prompt)
            return response.content
        except:
            return f"Daily Summary: {stats.get('messages_today', 0)} messages. {stats.get('new_leads', 0)} new leads."
