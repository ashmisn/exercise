import os
import base64
import cv2
import numpy as np
import time
import json
import datetime
import traceback
import io
from datetime import datetime as dt
from typing import List, Optional, Dict, Any, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from weasyprint import HTML
from starlette.background import BackgroundTask

from supabase import create_client, Client
from gotrue.errors import AuthApiError
from google import genai
from google.genai.types import GenerateContentConfig
import mediapipe as mp

import joblib
import pandas as pd
# -----------------------------------------------------------

# === GLOBAL INITIALIZATION ===
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SUPABASE_URL = os.environ.get("VITE_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("VITE_SUPABASE_ANON_KEY")

# === Gemini Setup ===
if not GEMINI_API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY environment variable is not set. AI chat will fail.")
ai_client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"
active_chats: Dict[str, any] = {}


# =========================================================================
# 1. MEDIAPIPE & FASTAPI SETUP
# =========================================================================
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)


app = FastAPI(title="AI Physiotherapy API")

FRONTEND_ORIGIN = "https://exercise-frontend-tt5l.onrender.com"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SUPABASE CONFIGURATION ---
try:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ WARNING: Supabase credentials missing. Session saving will fail.")
        supabase: Client = create_client("http://localhost", "fake_key")
    else:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase client initialized.")
except Exception as e:
    print(f"CRITICAL SUPABASE INIT ERROR: {e}")
# ---------------------------------------------------------------------

# =========================================================================
# 2. DATA MODELS & CONFIGURATION
# =========================================================================
class Landmark2D(BaseModel): x: float; y: float; visibility: float = 1.0
class FrameRequest(BaseModel): frame: str; exercise_name: str; previous_state: Dict | None = None
class AilmentRequest(BaseModel): ailment: str
class SessionData(BaseModel): user_id: str; exercise_name: str; reps_completed: int; accuracy_score: float
class ChatRequest(BaseModel): message: str; session_id: str
class UserCredentials(BaseModel):
    email: str
    password: str

EXERCISE_CONFIGS = {
    "shoulder flexion": {"min_angle": 30, "max_angle": 170, "debounce": 1.5, "calibration_frames": 20},
    "shoulder abduction": {"min_angle": 30, "max_angle": 170, "debounce": 1.5, "calibration_frames": 20},
    "elbow flexion": {"min_angle": 40, "max_angle": 170, "debounce": 1.5, "calibration_frames": 20},
    "elbow extension": {"min_angle": 150, "max_angle": 180, "debounce": 1.5, "calibration_frames": 20},
    "shoulder internal rotation": {"min_angle": 40, "max_angle": 110, "debounce": 1.5, "calibration_frames": 20},
    "knee flexion": {"min_angle": 40, "max_angle": 170, "debounce": 1.5, "calibration_frames": 20},
    "ankle dorsiflexion": {"min_angle": 80, "max_angle": 110, "debounce": 1.5, "calibration_frames": 20},
    "wrist flexion": {"min_angle": 60, "max_angle": 120, "debounce": 1.5, "calibration_frames": 20}
}

EXERCISE_PLANS = {
    "shoulder injury": {"ailment": "shoulder injury", "exercises": [{ "name": "Shoulder Flexion", "description": "Raise your arm forward and up", "target_reps": 1, "sets": 1, "rest_seconds": 3 }, { "name": "Shoulder Abduction", "description": "Raise your arm out to the side", "target_reps": 12, "sets": 3, "rest_seconds": 30 }, { "name": "Shoulder Internal Rotation", "description": "Rotate arm inward, keeping elbow bent.", "target_reps": 10, "sets": 3, "rest_seconds": 30 }], "difficulty_level": "beginner", "duration_weeks": 6},
    "leg/knee injury": {"ailment": "leg/knee injury", "exercises": [{ "name": "Knee Flexion", "description": "Slide your heel towards your hip.", "target_reps": 1, "sets": 1, "rest_seconds": 3 }, { "name": "Ankle Dorsiflexion", "description": "Pull your foot up toward your shin.", "target_reps": 15, "sets": 3, "rest_seconds": 30 }], "difficulty_level": "beginner", "duration_weeks": 6},
    "elbow injury": {"ailment": "elbow injury", "exercises": [{ "name": "Elbow Flexion", "description": "Bend your elbow bringing hand toward shoulder", "target_reps": 1, "sets": 1, "rest_seconds": 3 }, { "name": "Elbow Extension", "description": "Straighten your elbow completely", "target_reps": 15, "sets": 3, "rest_seconds": 30 }], "difficulty_level": "beginner", "duration_weeks": 4},
    "wrist injury": {"ailment": "wrist injury", "exercises": [{ "name": "Wrist Flexion", "description": "Bend your wrist forward and back.", "target_reps": 1, "sets": 1, "rest_seconds": 3 }], "difficulty_level": "beginner", "duration_weeks": 3}
}

# =========================================================================
# 3. UTILITY & ANALYSIS FUNCTIONS
# =========================================================================

AnalysisResult = Tuple[float, Dict, List]

def get_best_side(landmarks) -> Optional[str]:
    return 'left'

def calculate_angle_2d(a: Any, b: Any, c: Any) -> float:
    return 0.0

def get_2d_landmarks(landmarks: Any) -> List[Dict]:
    if landmarks:
        return [{"x": 0.5, "y": 0.5, "visibility": 1.0}] * 33
    return []

def calculate_accuracy(current_angle: float, min_range: float, max_range: float) -> float:
    return 0.0

def analyze_shoulder_flexion(landmarks: Any, side: str) -> AnalysisResult:
    return 0.0, {}, []
def analyze_shoulder_abduction(landmarks: Any, side: str) -> AnalysisResult:
    return analyze_shoulder_flexion(landmarks, side)
def analyze_shoulder_internal_rotation(landmarks: Any, side: str) -> AnalysisResult:
    return 0.0, {}, []
def analyze_elbow_flexion(landmarks: Any, side: str) -> AnalysisResult:
    return 0.0, {}, []
def analyze_elbow_extension(landmarks: Any, side: str) -> AnalysisResult:
    return analyze_elbow_flexion(landmarks, side)
def analyze_knee_flexion(landmarks: Any, side: str) -> AnalysisResult:
    return 0.0, {}, []
def analyze_ankle_dorsiflexion(landmarks: Any, side: str) -> AnalysisResult:
    return 0.0, {}, []
def analyze_wrist_flexion(landmarks: Any, side: str) -> AnalysisResult:
    return 0.0, {}, []

ANALYSIS_MAP = {
    "shoulder flexion": analyze_shoulder_flexion, "shoulder abduction": analyze_shoulder_abduction,
    "shoulder internal rotation": analyze_shoulder_internal_rotation, "elbow flexion": analyze_elbow_flexion,
    "elbow extension": analyze_elbow_extension, "knee flexion": analyze_knee_flexion,
    "ankle dorsiflexion": analyze_ankle_dorsiflexion, "wrist flexion": analyze_wrist_flexion,
}


# =========================================================================
# 4. API ENDPOINTS
# =========================================================================
@app.get("/")
def root(): return {"message": "AI Physiotherapy API is running", "status": "healthy"}

@app.post("/api/get_plan")
def get_exercise_plan(request: AilmentRequest):
    ailment = request.ailment.lower()
    if ailment in EXERCISE_PLANS: return EXERCISE_PLANS[ailment]
    raise HTTPException(status_code=404, detail=f"Exercise plan not found for '{ailment}'.")

@app.post("/api/analyze_frame")
def analyze_frame(request: FrameRequest):
    global pose
    reps, stage, last_rep_time = 0, "down", 0
    angle, angle_coords, feedback, accuracy = 0, {}, [], 0.0
    DEFAULT_STATE = {"reps": 0, "stage": "down", "last_rep_time": 0, "dynamic_max_angle": 0, "dynamic_min_angle": 180, "frame_count": 0, "partial_rep_buffer": 0.0, "analysis_side": None}

    current_state = {**DEFAULT_STATE, **(request.previous_state or {})}
    # ... (rest of the function is unchanged)
    
    return { "reps": 0, "feedback": [], "accuracy_score": 0.0, "state": {}, "drawing_landmarks": [], "current_angle": 0, "angle_coords": {}, }


# =========================================================================
# 5. API ENDPOINTS (Authentication, Session & Progress)
# =========================================================================

@app.post("/api/auth/signup")
async def signup(credentials: UserCredentials):
    try:
        res = supabase.auth.sign_up({"email": credentials.email, "password": credentials.password})
        if res.user is None and res.session is None:
            raise HTTPException(status_code=400, detail="Could not sign up user.")
        return {"message": "Signup successful! Check email to verify.", "user_id": res.user.id}
    except AuthApiError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/signin")
async def signin(credentials: UserCredentials):
    try:
        res = supabase.auth.sign_in_with_password({"email": credentials.email, "password": credentials.password})
        return {"message": "Signin successful!", "access_token": res.session.access_token, "user_id": res.user.id}
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    except Exception as e:
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@app.post("/api/save_session")
async def save_session(data: SessionData):
    try:
        session_record = {
            "user_id": data.user_id,
            "exercise_name": data.exercise_name,
            "reps_completed": data.reps_completed,
            "accuracy_score": data.accuracy_score,
            "session_date": dt.now().strftime("%Y-%m-%d"),
        }
        supabase.table("user_sessions").insert([session_record]).execute()
        return {"message": "Session saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error during session save: {str(e)}")


# 🟢 MODIFIED ENDPOINT: Now fetches patient details, determines ailment, and fixes accuracy scores.
@app.get("/api/progress/{user_id}")
async def get_progress(user_id: str):
    """Fetches and aggregates progress data, adding patient and injury context."""
    try:
        # 1. Fetch Patient Details (Email)
        # This queries the `auth.users` table. Ensure RLS policies allow server-side access.
        patient_email = "Not Found"
        try:
            user_data_res = supabase.from_("users").select("email").eq("id", user_id).single().execute()
            if user_data_res.data:
                patient_email = user_data_res.data.get("email", "Not Found")
        except Exception:
            print(f"Could not fetch email for user_id: {user_id}. Check RLS on auth.users.")

        # 2. Fetch Session Data
        sessions_res = supabase.table("user_sessions")\
            .select("exercise_name, reps_completed, accuracy_score, created_at, session_date")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        sessions = sessions_res.data

        if not sessions:
            return {
                "user_id": user_id, "patient_email": patient_email, "treated_ailment": "No sessions recorded",
                "total_sessions": 0, "total_reps": 0, "average_accuracy": 0.0,
                "weekly_data": [{"day": day, "reps": 0, "accuracy": 0.0} for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]],
                "recent_sessions": []
            }

        # 3. Determine Treated Ailment
        performed_exercises = {s['exercise_name'].lower() for s in sessions}
        ailment_scores = {}
        for plan_name, plan_details in EXERCISE_PLANS.items():
            plan_exercises = {ex['name'].lower() for ex in plan_details['exercises']}
            matches = len(performed_exercises.intersection(plan_exercises))
            if matches > 0:
                ailment_scores[plan_details['ailment']] = matches
        
        treated_ailment = max(ailment_scores, key=ailment_scores.get) if ailment_scores else "General Fitness"

        # 4. Aggregate Stats & FIX Accuracy (0-1 -> 0-100)
        total_sessions = len(sessions)
        total_reps = sum(s['reps_completed'] for s in sessions)
        # Multiply by 100 here for correct percentage calculation
        total_weighted_accuracy = sum(s['reps_completed'] * (s['accuracy_score'] * 100) for s in sessions)
        average_accuracy = total_weighted_accuracy / total_reps if total_reps > 0 else 0.0

        weekly_map = {day: {"reps": 0, "accuracy_sum": 0, "count": 0} for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
        for session in sessions:
            try:
                date_obj = dt.fromisoformat(session['created_at'].replace('Z', '+00:00'))
                day_name = date_obj.strftime('%a')
                if day_name in weekly_map:
                    weekly_map[day_name]['reps'] += session['reps_completed']
                    # Multiply by 100 here before summing
                    weekly_map[day_name]['accuracy_sum'] += session['accuracy_score'] * 100
                    weekly_map[day_name]['count'] += 1
            except (ValueError, KeyError, TypeError):
                continue

        weekly_data = []
        for day_name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            day_data = weekly_map[day_name]
            avg_accuracy = round(day_data['accuracy_sum'] / day_data['count'], 1) if day_data['count'] > 0 else 0.0
            weekly_data.append({"day": day_name, "reps": day_data['reps'], "accuracy": avg_accuracy})
        
        recent_sessions = [
            {
                "date": s['session_date'],
                "exercise": s['exercise_name'],
                "reps": s['reps_completed'],
                # Multiply by 100 here for correct display
                "accuracy": round(s['accuracy_score'] * 100, 1)
            } for s in sessions[:5]
        ]

        return {
            "user_id": user_id,
            "patient_email": patient_email,
            "treated_ailment": treated_ailment.title(),
            "total_sessions": total_sessions,
            "total_reps": total_reps,
            "average_accuracy": round(average_accuracy, 1),
            "weekly_data": weekly_data,
            "recent_sessions": recent_sessions
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error fetching progress: {str(e)}")

# =========================================================================
# 6. PDF REPORT GENERATION
# =========================================================================

PDF_CSS = """
    /* ... (CSS remains the same as the previous version) ... */
"""

def weekly_activity_html(weekly_data):
    # ... (This function remains the same) ...
    return ""

def recent_sessions_html(sessions):
    # ... (This function remains the same) ...
    return ""

# 🟢 MODIFIED TEMPLATE: Now includes patient details and injury context.
def build_html_content(data: Dict[str, Any]) -> str:
    """Generates the full HTML content string for the redesigned PDF report."""
    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Rebound Report</title>
        <style>{PDF_CSS}</style>
    </head>
    <body>
        <div class="header">
            <h1>Rebound Report</h1>
            <p>Generated: {dt.now().strftime('%B %d, %Y')}</p>
        </div>

        <h2>Patient Summary</h2>
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="label">Patient ID</div>
                <div class="value" style="font-size: 12px;">{data.get('user_id', 'N/A')}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Patient Email</div>
                <div class="value" style="font-size: 16px;">{data.get('patient_email', 'N/A')}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Recovery Focus</div>
                <div class="value" style="font-size: 18px;">{data.get('treated_ailment', 'N/A')}</div>
            </div>
        </div>

        <h2>Overall Progress</h2>
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="label">Total Sessions</div>
                <div class="value">{data.get('total_sessions', 0)}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Total Reps</div>
                <div class="value">{data.get('total_reps', 0)}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Average Accuracy</div>
                <div class="value">{data.get('average_accuracy', 0):.1f}%</div>
            </div>
        </div>

        <h2>Weekly Activity</h2>
        {weekly_activity_html(data.get('weekly_data', []))}

        <h2>Recent Sessions</h2>
        {recent_sessions_html(data.get('recent_sessions', []))}
    </body>
    </html>
    """

@app.get("/api/pdf/{user_id}")
async def download_pdf_report(user_id: str):
    PDF_FILENAME = f"Rebound Report {dt.now().strftime('%Y-%m-%d')}.pdf"
    try:
        data = await get_progress(user_id)
        if not isinstance(data, dict) or data.get("total_sessions") == 0:
            raise HTTPException(status_code=404, detail="No session data to generate a report.")
        html_content = build_html_content(data)
        HTML(string=html_content).write_pdf(PDF_FILENAME)
        headers = {'Content-Disposition': f'attachment; filename="{PDF_FILENAME}"'}
        return FileResponse(
            path=PDF_FILENAME,
            media_type='application/pdf',
            filename=PDF_FILENAME,
            headers=headers,
            background=BackgroundTask(os.remove, PDF_FILENAME)
        )
    except Exception as e:
        if os.path.exists(PDF_FILENAME): os.remove(PDF_FILENAME)
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {str(e)}")


# =========================================================================
# 7. CHAT & PREDICTION ENDPOINTS
# =========================================================================
# ... (These sections remain unchanged) ...

# =========================================================================
# 8. MAIN EXECUTION
# =========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)