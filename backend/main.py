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
    "shoulder injury": {"ailment": "shoulder injury", "exercises": [{ "name": "Shoulder Flexion", "description": "Raise your arm forward and up", "target_reps": 5, "sets": 3, "rest_seconds": 30 }, { "name": "Shoulder Abduction", "description": "Raise your arm out to the side", "target_reps": 12, "sets": 3, "rest_seconds": 30 }, { "name": "Shoulder Internal Rotation", "description": "Rotate arm inward, keeping elbow bent.", "target_reps": 10, "sets": 3, "rest_seconds": 30 }], "difficulty_level": "beginner", "duration_weeks": 6},
    "leg/knee injury": {"ailment": "leg/knee injury", "exercises": [{ "name": "Knee Flexion", "description": "Slide your heel towards your hip.",  "target_reps": 5, "sets": 3, "rest_seconds": 30 }, { "name": "Ankle Dorsiflexion", "description": "Pull your foot up toward your shin.", "target_reps": 15, "sets": 3, "rest_seconds": 30 }], "difficulty_level": "beginner", "duration_weeks": 6},
    "elbow injury": {"ailment": "elbow injury", "exercises": [{ "name": "Elbow Flexion", "description": "Bend your elbow bringing hand toward shoulder",  "target_reps": 5, "sets": 3, "rest_seconds": 30}, { "name": "Elbow Extension", "description": "Straighten your elbow completely", "target_reps": 15, "sets": 3, "rest_seconds": 30 }], "difficulty_level": "beginner", "duration_weeks": 4},
    "wrist injury": {"ailment": "wrist injury", "exercises": [{ "name": "Wrist Flexion", "description": "Bend your wrist forward and back.",  "target_reps": 5, "sets": 3, "rest_seconds": 30}], "difficulty_level": "beginner", "duration_weeks": 3}
}

# =========================================================================
# 3. UTILITY & ANALYSIS FUNCTIONS
# =========================================================================
AnalysisResult = Tuple[float, Dict, List]
def get_best_side(landmarks) -> Optional[str]: return 'left'
def calculate_angle_2d(a: Any, b: Any, c: Any) -> float: return 0.0
def get_2d_landmarks(landmarks: Any) -> List[Dict]: return [{"x": 0.5, "y": 0.5, "visibility": 1.0}] * 33 if landmarks else []
def calculate_accuracy(current_angle: float, min_range: float, max_range: float) -> float: return 0.0
def analyze_shoulder_flexion(landmarks: Any, side: str) -> AnalysisResult: return 0.0, {}, []
def analyze_shoulder_abduction(landmarks: Any, side: str) -> AnalysisResult: return analyze_shoulder_flexion(landmarks, side)
def analyze_shoulder_internal_rotation(landmarks: Any, side: str) -> AnalysisResult: return 0.0, {}, []
def analyze_elbow_flexion(landmarks: Any, side: str) -> AnalysisResult: return 0.0, {}, []
def analyze_elbow_extension(landmarks: Any, side: str) -> AnalysisResult: return analyze_elbow_flexion(landmarks, side)
def analyze_knee_flexion(landmarks: Any, side: str) -> AnalysisResult: return 0.0, {}, []
def analyze_ankle_dorsiflexion(landmarks: Any, side: str) -> AnalysisResult: return 0.0, {}, []
def analyze_wrist_flexion(landmarks: Any, side: str) -> AnalysisResult: return 0.0, {}, []

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
    # We must rely on the global 'pose' object for performance stability.
    global pose 
    
    reps, stage, last_rep_time = 0, "down", 0
    angle, angle_coords, feedback, accuracy = 0, {}, [], 0.0
    DEFAULT_STATE = {"reps": 0, "stage": "down", "last_rep_time": 0, "dynamic_max_angle": 0, "dynamic_min_angle": 180, "frame_count": 0, "partial_rep_buffer": 0.0, "analysis_side": None}
    
    current_state = {**DEFAULT_STATE, **(request.previous_state or {})}
    reps = current_state["reps"]
    stage = current_state["stage"]
    last_rep_time = current_state["last_rep_time"]
    dynamic_max_angle = current_state["dynamic_max_angle"]
    dynamic_min_angle = current_state["dynamic_min_angle"]
    frame_count = current_state["frame_count"]
    partial_rep_buffer = current_state["partial_rep_buffer"]
    analysis_side = current_state["analysis_side"]

    try:
        header, encoded = request.frame.split(',', 1) if ',' in request.frame else ('', request.frame)
        img_data = base64.b64decode(encoded)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None or frame.size == 0: 
            return {"reps": reps, "feedback": [{"type": "warning", "message": "Video stream data corrupted."}], "accuracy_score": 0.0, "state": current_state, "drawing_landmarks": [], "current_angle": 0, "angle_coords": {}}

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)
        
        landmarks = None
        
        if not results.pose_landmarks:
            feedback.append({"type": "warning", "message": "No pose detected. Adjust camera view."})
        else:
            landmarks = results.pose_landmarks.landmark
            exercise_name = request.exercise_name.lower()
            if analysis_side is None: analysis_side = get_best_side(landmarks)
            
            if analysis_side is None:
                feedback.append({"type": "warning", "message": "Please turn sideways or expose one full side."})
            else:
                config = EXERCISE_CONFIGS.get(exercise_name, {})
                if not config: feedback.append({"type": "warning", "message": f"Configuration not found for: {exercise_name}"})
                else:
                    analysis_func = ANALYSIS_MAP.get(exercise_name)
                    if analysis_func:
                        angle, angle_coords, analysis_feedback = analysis_func(landmarks, analysis_side)
                        feedback.extend(analysis_feedback)
                        
                        if not analysis_feedback:
                            CALIBRATION_FRAMES, DEBOUNCE_TIME = config['calibration_frames'], config['debounce']
                            current_time = time.time()
                            
                            if frame_count < CALIBRATION_FRAMES and reps == 0:
                                dynamic_max_angle = max(dynamic_max_angle, angle)
                                dynamic_min_angle = min(dynamic_min_angle, angle)
                                frame_count += 1
                                feedback.append({"type": "progress", "message": f"Calibrating range ({frame_count}/{CALIBRATION_FRAMES}). Move fully from start to finish position."})
                                accuracy = 0.0
                                
                            if frame_count >= CALIBRATION_FRAMES or reps > 0:
                                CALIBRATED_MIN_ANGLE, CALIBRATED_MAX_ANGLE = dynamic_min_angle, dynamic_max_angle
                                MIN_ANGLE_THRESHOLD_FULL, MAX_ANGLE_THRESHOLD_FULL = CALIBRATED_MIN_ANGLE + 5, CALIBRATED_MAX_ANGLE - 5
                                MIN_ANGLE_THRESHOLD_PARTIAL, MAX_ANGLE_THRESHOLD_PARTIAL = CALIBRATED_MIN_ANGLE + 20, CALIBRATED_MAX_ANGLE - 20
                                frame_accuracy = calculate_accuracy(angle, CALIBRATED_MIN_ANGLE, CALIBRATED_MAX_ANGLE)
                                accuracy = frame_accuracy

                                if angle < MIN_ANGLE_THRESHOLD_PARTIAL:
                                    stage = "up"
                                    feedback.append({"type": "instruction", "message": "Hold contracted position at the top!" if angle < MIN_ANGLE_THRESHOLD_FULL else "Go deeper for a full rep."})
                                
                                if angle > MAX_ANGLE_THRESHOLD_PARTIAL and stage == "up":
                                    if current_time - last_rep_time > DEBOUNCE_TIME:
                                        rep_amount = 0.0
                                        if angle > MAX_ANGLE_THRESHOLD_FULL: rep_amount, success_message = 1.0, "FULL Rep Completed! Well done."
                                        else: rep_amount, success_message = 0.5, "Partial Rep (50%) counted. Complete the movement."
                                            
                                        if rep_amount > 0:
                                            stage, partial_rep_buffer, last_rep_time = "down", partial_rep_buffer + rep_amount, current_time
                                            if partial_rep_buffer >= 1.0: reps, partial_rep_buffer = reps + int(partial_rep_buffer), partial_rep_buffer % 1.0
                                            feedback.append({"type": "encouragement", "message": f"{success_message} Total reps: {reps}"})
                                        else: feedback.append({"type": "warning", "message": "Incomplete return to starting position."})
                                    else: feedback.append({"type": "warning", "message": "Slow down! Ensure controlled return."})
                                    
                                if not any(f['type'] in ['warning', 'instruction', 'encouragement'] for f in feedback):
                                    if stage == 'up' and angle > MIN_ANGLE_THRESHOLD_FULL: feedback.append({"type": "progress", "message": "Push further to the maximum range."})
                                    elif stage == 'down' and angle < MAX_ANGLE_THRESHOLD_FULL: feedback.append({"type": "progress", "message": "Return fully to the starting position."})
                                    elif stage == 'down': feedback.append({"type": "progress", "message": "Ready to start the next rep."})
                                    elif stage == 'up': feedback.append({"type": "progress", "message": "Controlled movement upward."})
                    else: feedback.append({"type": "warning", "message": "Analysis function missing."})
        
        # 🟢 FIX: Convert accuracy from a decimal (e.g., 0.95) to a percentage (e.g., 95.0)
        final_accuracy_display = accuracy * 100

        drawing_landmarks = get_2d_landmarks(landmarks) if landmarks else []
        new_state = {"reps": reps, "stage": stage, "angle": round(angle, 1), "last_rep_time": last_rep_time, "dynamic_max_angle": dynamic_max_angle, "dynamic_min_angle": dynamic_min_angle, "frame_count": frame_count, "partial_rep_buffer": partial_rep_buffer, "analysis_side": analysis_side}

        return {
            "reps": reps, 
            "feedback": feedback if feedback else [{"type": "progress", "message": "Processing..."}], 
            "accuracy_score": round(final_accuracy_display, 2), 
            "state": new_state, 
            "drawing_landmarks": drawing_landmarks, 
            "current_angle": round(angle, 1), 
            "angle_coords": angle_coords, 
            "min_angle": round(dynamic_min_angle, 1), 
            "max_angle": round(dynamic_max_angle, 1), 
            "side": analysis_side
        }

    except Exception as e:
        # Crucial for catching the intermittent MediaPipe timestamp error 
        # and preventing the server from crashing into a 502 error state.
        error_detail = str(e)
        if "Packet timestamp mismatch" in error_detail or "CalculatorGraph::Run() failed" in error_detail:
              print(f"Handled MediaPipe Timestamp Error: {error_detail}")
              # Return a temporary error message that allows the client to retry
              raise HTTPException(status_code=400, detail="Transient analysis error. Please try again.")
        
        print(f"CRITICAL ERROR in analyze_frame: {error_detail}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected server error during analysis: {error_detail}")

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


@app.get("/api/progress/{user_id}")
async def get_progress(user_id: str):
    """Fetches and aggregates progress data, adding patient and injury context."""
    try:
        # Fetch Patient Details (Email)
        patient_email = "Not Found"
        try:
            # Note: This query requires RLS policies on `auth.users` to be configured
            # to allow service roles to read the email column.
            user_data_res = supabase.from_("users").select("email").eq("id", user_id).single().execute()
            if user_data_res.data:
                patient_email = user_data_res.data.get("email", "Not Found")
        except Exception:
            print(f"Could not fetch email for user_id: {user_id}. Check RLS on auth.users.")

        # Fetch Session Data
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

        # Determine Treated Ailment
        performed_exercises = {s['exercise_name'].lower() for s in sessions}
        ailment_scores = {}
        for plan_name, plan_details in EXERCISE_PLANS.items():
            plan_exercises = {ex['name'].lower() for ex in plan_details['exercises']}
            matches = len(performed_exercises.intersection(plan_exercises))
            if matches > 0:
                ailment_scores[plan_details['ailment']] = matches
        
        treated_ailment = max(ailment_scores, key=ailment_scores.get) if ailment_scores else "General Fitness"

        # Aggregate Stats & FIX Accuracy (Assume DB stores 0-100)
        total_sessions = len(sessions)
        total_reps = sum(s['reps_completed'] for s in sessions)
        total_weighted_accuracy = sum(s['reps_completed'] * s['accuracy_score'] for s in sessions)
        average_accuracy = total_weighted_accuracy / total_reps if total_reps > 0 else 0.0

        weekly_map = {day: {"reps": 0, "accuracy_sum": 0, "count": 0} for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
        for session in sessions:
            try:
                date_obj = dt.fromisoformat(session['created_at'].replace('Z', '+00:00'))
                day_name = date_obj.strftime('%a')
                if day_name in weekly_map:
                    weekly_map[day_name]['reps'] += session['reps_completed']
                    weekly_map[day_name]['accuracy_sum'] += session['accuracy_score']
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
                "accuracy": round(s['accuracy_score'], 1)
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

# 🟢 FIX: The complete, non-empty CSS is here.
PDF_CSS = """
    @page {
        size: A4;
        margin: 1.5cm;
    }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        color: #333;
        font-size: 11px;
    }
    .header {
        text-align: center;
        border-bottom: 2px solid #4A90E2;
        padding-bottom: 15px;
        margin-bottom: 30px;
    }
    .header h1 {
        margin: 0;
        color: #4A90E2;
        font-size: 26px;
        font-weight: 600;
    }
    .header p {
        margin: 5px 0 0;
        color: #777;
    }
    h2 {
        font-size: 16px;
        color: #333;
        border-bottom: 1px solid #eee;
        padding-bottom: 8px;
        margin-top: 30px;
        margin-bottom: 20px;
        font-weight: 600;
        page-break-after: avoid;
    }
    .kpi-container {
        display: flex;
        gap: 15px;
        justify-content: space-around;
        text-align: center;
        page-break-inside: avoid;
    }
    .kpi-card {
        background-color: #f9f9f9;
        border: 1px solid #eee;
        border-radius: 8px;
        padding: 15px;
        flex: 1;
    }
    .kpi-card .label {
        font-size: 11px;
        color: #666;
        margin-bottom: 8px;
        text-transform: uppercase;
    }
    .kpi-card .value {
        font-size: 24px;
        font-weight: 600;
        color: #4A90E2;
    }
    .week-day {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        page-break-inside: avoid;
    }
    .day-label {
        width: 40px;
        font-weight: bold;
    }
    .bars {
        flex-grow: 1;
        height: 22px;
        background-color: #f0f0f0;
        border-radius: 4px;
        position: relative;
    }
    .rep-bar {
        position: absolute;
        height: 100%;
        background-color: #4A90E2;
        border-radius: 4px;
    }
    .stats {
        width: 120px;
        text-align: right;
        font-size: 11px;
        color: #555;
    }
    .session-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        page-break-inside: avoid;
    }
    .session-table th, .session-table td {
        border-bottom: 1px solid #eee;
        padding: 10px;
        text-align: left;
    }
    .session-table th {
        font-weight: bold;
        background-color: #f9f9f9;
    }
    .accuracy-cell { font-weight: bold; }
"""

# 🟢 FIX: The complete, non-empty function bodies are here.
def weekly_activity_html(weekly_data):
    html = ""
    max_reps = max([d['reps'] for d in weekly_data] + [1])
    for day in weekly_data:
        width_percent = (day['reps'] / max_reps) * 100 if max_reps > 0 else 0
        html += f"""
        <div class="week-day">
            <div class="day-label">{day['day']}</div>
            <div class="bars">
                <div class="rep-bar" style="width:{width_percent}%;"></div>
            </div>
            <div class="stats">{day['reps']} reps | {day['accuracy']}% avg</div>
        </div>"""
    return html

def recent_sessions_html(sessions):
    rows = ""
    for s in sessions:
        try:
            date_str = dt.fromisoformat(s['date']).strftime("%b %d, %Y")
        except (ValueError, TypeError):
            date_str = s.get('date', 'N/A')

        color = "#16a34a" if s['accuracy'] > 90 else ("#f59e0b" if s['accuracy'] > 75 else "#dc2626")
        rows += f"""
        <tr>
            <td>{date_str}</td>
            <td>{s.get('exercise', 'N/A')}</td>
            <td>{s.get('reps', 'N/A')}</td>
            <td class="accuracy-cell" style="color: {color};">{s.get('accuracy', 0)}%</td>
        </tr>"""

    return f"""
        <table class="session-table">
            <thead>
                <tr><th>Date</th><th>Exercise</th><th>Reps</th><th>Accuracy</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    """

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
                <div class="label">Patient Email</div>
                <div class="value" style="font-size: 14px;">{data.get('patient_email', 'N/A')}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Recovery Focus</div>
                <div class="value">{data.get('treated_ailment', 'N/A')}</div>
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
        traceback.print_exc()
        if os.path.exists(PDF_FILENAME): os.remove(PDF_FILENAME)
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF report: {str(e)}")


# =========================================================================
# 7. CHAT & PREDICTION ENDPOINTS
# =========================================================================
PREDEFINED_RESPONSES = {
    "frequency": "For optimal recovery, exercise 3-5 times per week. Allow at least one day of rest between sessions for the same muscle group. Consistency is key. Listen to your body and adjust as needed.",
    "rest": "Rest days are crucial for recovery! Your muscles need time to repair and strengthen. Never skip rest days. During rest, your body builds back stronger. Consider gentle stretching on rest days.",
    "correct": "To ensure correct form: 1) Move slowly and deliberately 2) Maintain proper posture 3) Breathe naturally - don't hold your breath 4) Stay within pain-free range 5) Use a mirror to check alignment 6) Focus on quality over quantity.",
    "warm": "Always warm up before exercises! Do 5-10 minutes of light cardio like walking. Gentle arm circles help warm up shoulders. This increases blood flow and reduces injury risk.",
    "progress": "Track your progress by: 1) Noting pain levels (should decrease over time) 2) Range of motion improvements 3) Number of reps completed 4) Daily activities becoming easier. Progress takes time - be patient!",
    "set": "The target sets and reps in your plan are a guide. Listen to your body. If you can complete the target with good form, aim for it! If not, reduce the number and focus on perfect technique.",
    "modify": "If an exercise feels too easy or causes mild pain, it might be time to **modify** it. You can increase reps, sets, or hold the end position longer. **Always consult your physical therapist** before making major changes.",
    "how long": "Rehabilitation length varies based on the injury's severity and your body's response. Typical plans are **4-8 weeks**, but consistent, gradual effort is more important than rushing the process.",
}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        user_message = request.message
        session_id = request.session_id
        message_lower = user_message.lower()
        for keyword, response in PREDEFINED_RESPONSES.items():
            if keyword in message_lower:
                return {"response": response}

        if session_id not in active_chats:
            system_instruction = ("You are Mia — a friendly, professional virtual rehabilitation assistant and coach...") # Instruction text omitted for brevity
            chat_session = ai_client.chats.create(
                model=MODEL_NAME,
                config=GenerateContentConfig(system_instruction=system_instruction)
            )
            active_chats[session_id] = chat_session
            print(f"New chat session created for ID: {session_id}")
        else:
            chat_session = active_chats[session_id]

        gemini_response = chat_session.send_message(user_message)
        bot_response = gemini_response.text
        return {"response": bot_response}

    except Exception as e:
        print(f"Error in /api/chat: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An AI or Server error occurred: {str(e)}")


MODEL_PATH = 'model/cph_model.joblib'
try:
    CPH_MODEL = joblib.load(MODEL_PATH)
except FileNotFoundError:
    print(f"⚠️ WARNING: Model file not found at {MODEL_PATH}. Prediction endpoint will fail.")
    CPH_MODEL = None

MODEL_FEATURES = [
    "Age", "Health_Score", "Injury_Ankle injury", "Injury_Back injury",
    "Injury_Calf injury", "Injury_Coronavirus", "Injury_Foot injury",
    "Injury_Groin injury", "Injury_Hamstring injury", "Injury_Hamstring strain",
    "Injury_Ill", "Injury_Knee injury", "Injury_Knee surgery", "Injury_Knock",
    "Injury_Shoulder injury", "Injury_ankle injury", "Injury_bruise",
    "Injury_calf injury", "Injury_groin injury", "Injury_hamstring injury",
    "Injury_hamstring strain", "Injury_ill", "Injury_knee injury",
    "Injury_muscle injury", "Injury_unknown injury", "Previous_injury",
    "Physio_adherence", "Complication_count", "Inflammation_marker"
]

class PredictionInput(BaseModel):
    Age: float = Field(..., description="Patient's age.")
    Health_Score: float = Field(..., description="General health rating (0.0 to 10.0).")
    Physio_adherence: float = Field(..., description="Compliance with rehab plan (0.0 to 1.0).")
    Complication_count: int = Field(..., description="Number of minor complications/setbacks.")
    Inflammation_marker: float = Field(..., description="Inflammation score.")
    Previous_injury: int = Field(0, description="1 if patient has previous injuries, 0 otherwise.")
    Injury_Type: str = Field(..., description="The current type of injury.")

@app.post("/api/predict_recovery")
def predict_recovery(data: PredictionInput):
    if CPH_MODEL is None:
        raise HTTPException(status_code=503, detail="Prediction model is not available or failed to load.")
    if not MODEL_FEATURES:
        raise HTTPException(status_code=500, detail="Model features are missing. Cannot prepare input data.")
    try:
        patient_df = pd.DataFrame(0.0, index=[0], columns=MODEL_FEATURES)
        input_dict = data.dict()
        for feature in ["Age", "Health_Score", "Physio_adherence", "Complication_count", "Inflammation_marker", "Previous_injury"]:
            if feature in patient_df.columns:
                patient_df.loc[0, feature] = input_dict[feature]
        injury_column_name = f"Injury_{input_dict['Injury_Type']}"
        if injury_column_name in patient_df.columns:
            patient_df.loc[0, injury_column_name] = 1.0
        else:
            print(f"Warning: Injury type '{injury_column_name}' not found in model features. Using default zero vector.")
        patient_input = patient_df[MODEL_FEATURES]
        median_recovery_time = CPH_MODEL.predict_median(patient_input)
        predicted_days = int(median_recovery_time) # Access first element of numpy array
        return {
            "status": "success",
            "median_recovery_days": predicted_days
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prediction processing failed: {str(e)}")

# =========================================================================
# 8. MAIN EXECUTION
# =========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
