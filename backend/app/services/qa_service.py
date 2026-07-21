import json
import os
import re
from typing import Dict, List, Any, Optional
from .stock_service import StockService

class QAService:
    def __init__(self):
        self.queries = []
        self.stock_service = StockService()
        self.load_queries()

    def load_queries(self):
        query_path = "data/common_queries.json"
        if os.path.exists(query_path):
            with open(query_path, "r") as f:
                self.queries = json.load(f)
            print(f"✅ Loaded {len(self.queries)} trained customer queries")
        else:
            print("⚠️ common_queries.json not found — using minimal fallback")
            self.queries = []

    def _score_match(self, user_msg: str, trained_query: str) -> int:
        """Smart scoring for common queries"""
        user = user_msg.lower()
        trained = trained_query.lower()
        score = 0

        # Exact phrase boost
        if trained in user or user in trained:
            score += 5

        # Entity keywords
        keywords = {
            "rep": ["rep", "rep no", "repno"],
            "stone": ["stone", "packet", "lgrd", "lg", "stone no"],
            "price": ["price", "cost", "how much", "₹", "rupees", "budget"],
            "video": ["video", "see video", "watch"],
            "certificate": ["certificate", "cert", "gia", "igi"],
            "appointment": ["book", "appointment", "viewing", "visit", "see in person"],
            "recommend": ["similar", "option", "show", "send", "recommend", "other"],
            "lab": ["lab grown", "lab", "natural", "cvd"],
        }

        for group, terms in keywords.items():
            if any(t in user for t in terms) and any(t in trained for t in terms):
                score += 2

        # Carat / shape mentions
        if re.search(r'\d+(\.\d+)?\s*ct', user) and re.search(r'\d+(\.\d+)?\s*ct', trained):
            score += 2

        return score

    def find_best_match(self, message: str) -> Optional[Dict]:
        best_score = 0
        best_match = None

        for q in self.queries:
            score = self._score_match(message, q["query"])
            if score > best_score:
                best_score = score
                best_match = q

        # Only return if reasonably confident
        return best_match if best_score >= 2 else None

    def generate_response(self, message: str, entities: Dict = None) -> Optional[Dict]:
        """Return trained response, enriched with real stock when possible"""
        match = self.find_best_match(message)
        if not match:
            return None

        intent = match.get("intent", "general_query")
        template = match.get("response_template", match.get("expected_response", "Thank you! How can I help further?"))

        # === Enrich with real stock data when relevant ===
        stock = None
        if intent in ["stock_query", "pricing", "media_request"] and entities:
            if entities.get("rep_no"):
                stock = self.stock_service.get_stock_by_rep_no(entities["rep_no"])
            elif entities.get("stone_no"):
                stock = self.stock_service.get_stock_by_stone_no(entities["stone_no"])

        if stock:
            # Use beautiful stock formatting
            formatted = self.stock_service.format_stock_response([stock])
            return {
                "response": formatted,
                "intent": intent,
                "source": "trained_qa+stock",
                "stock_results": [stock]
            }

        # Fill template with any known entities
        response = template
        if entities:
            for k, v in entities.items():
                if v:
                    response = response.replace("{" + k + "}", str(v))

        return {
            "response": response,
            "intent": intent,
            "source": "trained_qa",
            "follow_up": "Would you like more options or to book a viewing?"
        }
