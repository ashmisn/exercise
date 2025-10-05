"""
chat.py
Gemini (google-genai) wrapper. Lazy client init, in-memory sessions, send_message helper.
"""

import os
import logging
from typing import Dict, Any

from google import genai
from google.genai.types import GenerateContentConfig

log = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

_ai_client = None
def get_ai_client():
    global _ai_client
    if _ai_client is not None:
        return _ai_client
    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY not set; AI calls will fail.")
        _ai_client = genai.Client(api_key=None)
    else:
        _ai_client = genai.Client(api_key=GEMINI_API_KEY)
    return _ai_client

ai_client = get_ai_client()
active_chats: Dict[str, Any] = {}

SYSTEM_INSTRUCTION = (
    "You are a helpful and encouraging AI rehabilitation assistant. Your advice must be general and "
    "focused on safe, effective exercise form, recovery, and motivation. Always advise the user to "
    "consult their healthcare provider or physical therapist for specific medical advice, injury assessment, or changes to their treatment plan."
)

def create_chat_session(session_id: str):
    client = get_ai_client()
    chat_session = client.chats.create(model=MODEL_NAME, config=GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION))
    active_chats[session_id] = chat_session
    log.info("Created chat session %s", session_id)
    return chat_session

def send_message(session_id: str, message: str) -> str:
    client = get_ai_client()
    if session_id not in active_chats:
        create_chat_session(session_id)
    chat_session = active_chats[session_id]
    # SDK wrappers vary; attempt typical methods
    if hasattr(chat_session, "send_message"):
        resp = chat_session.send_message(message)
        return getattr(resp, "text", str(resp))
    else:
        resp = client.generate(model=MODEL_NAME, input=message)
        return getattr(resp, "text", str(resp))
