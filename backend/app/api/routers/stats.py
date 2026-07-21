from fastapi import APIRouter
from datetime import datetime, date
from collections import defaultdict
import time

router = APIRouter()

# Simple in-memory counters (for free tier demo)
daily_messages = defaultdict(int)
user_message_count = defaultdict(int)  # per user (whatsapp_id)
last_reset = date.today()

def increment_message(whatsapp_id: str):
    global last_reset
    today = date.today()
    if today != last_reset:
        daily_messages.clear()
        user_message_count.clear()
        last_reset = today
    
    daily_messages[today] += 1
    user_message_count[whatsapp_id] += 1

@router.get("/stats")
async def get_stats():
    today = date.today()
    return {
        "date": str(today),
        "messages_today": daily_messages[today],
        "unique_users_today": len(user_message_count),
        "top_users": sorted(user_message_count.items(), key=lambda x: x[1], reverse=True)[:5],
        "status": "healthy"
    }

@router.get("/stats/volume")
async def get_volume_simulation():
    """Simple simulation for preview UI"""
    today = date.today()
    return {
        "messages_today": daily_messages[today] or 487,
        "daily_limit": 1200,
        "users_active": len(user_message_count) or 142,
        "percent_used": round(((daily_messages[today] or 487) / 1200) * 100, 1)
    }
