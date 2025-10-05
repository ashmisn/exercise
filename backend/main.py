"""
main.py - FastAPI entrypoint that wires routes to the modular components.
Deploy with:
uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""

import os
import traceback
from datetime import datetime as dt
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .analysis import analyze_frame_base64
from .database import save_session_record, get_progress_for_user
from .chat import send_message, create_chat_session, active_chats
from .reports import generate_pdf_report
from .constants import EXERCISE_CONFIGS, EXERCISE_PLANS, PREDEFINED_RESPONSES

# ----- Schemas -----
class Landmark2D(BaseModel):
    x: float
    y: float
    visibility: float = 1.0

class FrameRequest(BaseModel):
    frame: str
    exercise_name: str
    previous_state: Optional[Dict] = None

class AilmentRequest(BaseModel):
    ailment: str

class SessionData(BaseModel):
    user_id: str
    exercise_name: str
    reps_completed: int
    accuracy_score: float

class ChatRequest(BaseModel):
    message: str
    session_id: str

# ----- App -----
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "https://exercise-frontend-tt5l.onrender.com")
app = FastAPI(title="AI Physiotherapy API (modular)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Routes -----
@app.get("/")
def root():
    return {"message": "AI Physiotherapy API is running", "status": "healthy"}

@app.post("/api/get_plan")
def get_exercise_plan(request: AilmentRequest):
    ailment = request.ailment.lower()
    if ailment in EXERCISE_PLANS:
        return EXERCISE_PLANS[ailment]
    available = list(EXERCISE_PLANS.keys())
    raise HTTPException(status_code=404, detail=f"Exercise plan not found for '{ailment}'. Available plans: {available}")

@app.post("/api/analyze_frame")
def analyze_frame_route(request: FrameRequest):
    # delegate full analysis to analysis.py
    return analyze_frame_base64(request.frame, request.exercise_name.lower(), request.previous_state, exercise_configs=EXERCISE_CONFIGS)

@app.post("/api/save_session")
async def save_session(data: SessionData):
    try:
        session_record = {
            "user_id": data.user_id,
            "exercise_name": data.exercise_name,
            "reps_completed": data.reps_completed,
            "accuracy_score": data.accuracy_score,
            "session_date": dt.utcnow().strftime("%Y-%m-%d")
        }
        res = save_session_record(session_record)
        if not res.get("ok", False):
            raise HTTPException(status_code=500, detail=f"Database insert failed. Error: {res.get('error')}")
        return {"message": "Session saved successfully"}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/progress/{user_id}")
async def get_progress(user_id: str):
    try:
        return get_progress_for_user(user_id)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pdf/{user_id}")
def download_progress_report(user_id: str):
    try:
        filepath = generate_pdf_report(user_id)
        return FileResponse(filepath, filename=f"mobility_report_{user_id}.pdf")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    try:
        m = payload.message.lower()
        for kw, resp in PREDEFINED_RESPONSES.items():
            if kw in m:
                return {"response": resp}

        if payload.session_id not in active_chats:
            create_chat_session(payload.session_id)

        bot_text = send_message(payload.session_id, payload.message)
        return {"response": bot_text}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ----- Local dev run -----
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")
