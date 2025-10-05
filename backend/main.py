import os
import base64
import cv2
import numpy as np
import time
import json
import datetime
import traceback
import requests
import io
import tempfile
from datetime import datetime as dt
from typing import List, Optional, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from weasyprint import HTML, CSS # Used for PDF generation

# --- REQUIRED: CORRECT IMPORTS FOR NEW GEMINI & SUPABASE ---
from supabase import create_client, Client
from google import genai # The new SDK entry point
from google.genai.types import GenerateContentConfig # Required type for system instruction
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
import mediapipe as mp
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

# -------------------------------------------------------------------------
# NOTE: Placeholder for Utility Functions (Must be defined in your scope)
def get_best_side(landmarks): return 'left'
def calculate_angle_2d(a, b, c): return 0.0
def get_2d_landmarks(landmarks): 
    # Placeholder: Returns a valid structure if landmarks are present
    if landmarks: 
        # In real code, this converts MediaPipe's normalized landmarks to your internal Landmark2D interface
        return [{"x": l.x, "y": l.y, "visibility": l.visibility} for l in landmarks if hasattr(l, 'visibility') and l.visibility > 0.0]
    return []

def calculate_accuracy(current_angle: float, min_range: float, max_range: float) -> float: return 0.0
ANALYSIS_MAP = {} # Assume populated with analysis functions
# -------------------------------------------------------------------------

# =========================================================================
# 4. API ENDPOINTS (analyze_frame FIX)
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
    reps = current_state["reps"]
    stage = current_state["stage"]
    last_rep_time = current_state["last_rep_time"]
    dynamic_max_angle = current_state["dynamic_max_angle"]
    dynamic_min_angle = current_state["dynamic_min_angle"]
    frame_count = current_state["frame_count"]
    partial_rep_buffer = current_state["partial_rep_buffer"]
    analysis_side = current_state["analysis_side"]

    landmarks = None
    drawing_landmarks = [] # Initialize to empty list

    try:
        header, encoded = request.frame.split(',', 1) if ',' in request.frame else ('', request.frame)
        img_data = base64.b64decode(encoded)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None or frame.size == 0: 
            return {"reps": reps, "feedback": [{"type": "warning", "message": "Video stream data corrupted."}], "accuracy_score": 0.0, "state": current_state, "drawing_landmarks": [], "current_angle": 0, "angle_coords": {}}

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)
        
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
                        # Placeholder: Replace with actual analysis function calls
                        # For demonstration, assume successful analysis gets angle and feedback
                        angle, angle_coords, analysis_feedback = 0, {}, []
                        # angle, angle_coords, analysis_feedback = analysis_func(landmarks, analysis_side)
                        
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
        
        # 🛑 CRITICAL FIX: Ensure drawing_landmarks is calculated here
        # It calls the utility function which returns [] if landmarks is None
        drawing_landmarks = get_2d_landmarks(landmarks) if landmarks else [] 
        
        final_accuracy_display = accuracy
        new_state = {"reps": reps, "stage": stage, "angle": round(angle, 1), "last_rep_time": last_rep_time, "dynamic_max_angle": dynamic_max_angle, "dynamic_min_angle": dynamic_min_angle, "frame_count": frame_count, "partial_rep_buffer": partial_rep_buffer, "analysis_side": analysis_side}

        # 🟢 FINAL RETURN: drawing_landmarks is now guaranteed to be a list ([] if empty)
        return {
            "reps": reps, 
            "feedback": feedback if feedback else [{"type": "progress", "message": "Processing..."}], 
            "accuracy_score": round(final_accuracy_display, 2), 
            "state": new_state, 
            "drawing_landmarks": drawing_landmarks, # <--- GUARANTEED NOT TO BE null
            "current_angle": round(angle, 1), 
            "angle_coords": angle_coords, 
            "min_angle": round(dynamic_min_angle, 1), 
            "max_angle": round(dynamic_max_angle, 1), 
            "side": analysis_side
        }

    except Exception as e:
        error_detail = str(e)
        if "Packet timestamp mismatch" in error_detail or "CalculatorGraph::Run() failed" in error_detail:
            print(f"Handled MediaPipe Timestamp Error: {error_detail}")
            raise HTTPException(status_code=400, detail="Transient analysis error. Please try again.")
        
        print(f"CRITICAL ERROR in analyze_frame: {error_detail}")
        traceback.print_exc()
        # Return a safe structure on a full server crash
        raise HTTPException(status_code=500, detail=f"Unexpected server error during analysis: {error_detail}")

# =========================================================================
# 5. API ENDPOINTS MODIFIED FOR SUPABASE (Session & Progress)
# =========================================================================

@app.post("/api/save_session")
async def save_session(data: SessionData):
    """Saves session data to the 'user_sessions' table in Supabase."""
    try:
        session_record = {
            "user_id": data.user_id,
            "exercise_name": data.exercise_name,
            "reps_completed": data.reps_completed,
            "accuracy_score": data.accuracy_score,
            "session_date": dt.now().strftime("%Y-%m-%d"), 
        }

        response = supabase.table("user_sessions").insert([session_record]).execute()
        
        if response.error:
            print(f"SUPABASE INSERT ERROR: {response.error.message}")
            raise HTTPException(
                status_code=500, 
                detail=f"Database insert failed. Error: {response.error.message}"
            )

        print(f"SUPABASE WRITE: Saved {data.reps_completed} reps for user {data.user_id}")
        return {"message": "Session saved successfully"}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error during session save: {str(e)}")

@app.get("/api/progress/{user_id}")
async def get_progress(user_id: str):
    """Fetches and aggregates progress data from Supabase for a given user."""
    try:
        response = supabase.table("user_sessions")\
            .select("exercise_name, reps_completed, accuracy_score, created_at, session_date")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        
        sessions = response.data
        
        if not sessions: 
            return {"user_id": user_id, "total_sessions": 0, "total_reps": 0, "average_accuracy": 0.0, "streak_days": 0, "weekly_data": [{"day": day, "reps": 0, "accuracy": 0.0} for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]], "recent_sessions": []}

        # --- Aggregate Logic (Full logic retained) ---
        total_sessions = len(sessions)
        total_reps = sum(s['reps_completed'] for s in sessions)
        average_accuracy = sum(s['reps_completed'] * s['accuracy_score'] for s in sessions) / total_reps if total_reps > 0 else 0.0

        recent_sessions = sessions[:5]

        weekly_map = {day: {"reps": 0, "accuracy_sum": 0, "count": 0} for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
        
        for session in sessions:
            try:
                date_obj = dt.fromisoformat(session['created_at']) 
                day_name = date_obj.strftime('%a')
                if day_name in weekly_map:
                    weekly_map[day_name]['reps'] += session['reps_completed']
                    weekly_map[day_name]['accuracy_sum'] += session['accuracy_score']
                    weekly_map[day_name]['count'] += 1
            except ValueError:
                continue

        weekly_data = []
        for day_name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            data = weekly_map[day_name]
            weekly_data.append({"day": day_name, "reps": data['reps'], "accuracy": round(data['accuracy_sum'] / data['count'], 1) if data['count'] > 0 else 0.0})

        return {
            "user_id": user_id, 
            "total_sessions": total_sessions, 
            "total_reps": total_reps, 
            "average_accuracy": round(average_accuracy, 1), 
            "streak_days": 0, 
            "weekly_data": weekly_data, 
            "recent_sessions": [{"date": s['session_date'], "exercise": s['exercise_name'], "reps": s['reps_completed'], "accuracy": round(s['accuracy_score'], 1)} for s in recent_sessions]
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error fetching progress: {str(e)}")

# =========================================================================
# 6. PDF REPORT GENERATION & ENDPOINT (Simplified Placeholder)
# =========================================================================
def weekly_activity_html(weekly_data): return ""
def generate_pdf_report(user_id: str): return None

@app.get("/api/pdf/{user_id}")
def download_progress_report(user_id: str): 
    # Return a 501 Not Implemented error to avoid silent failure if logic is missing
    raise HTTPException(status_code=501, detail="PDF generation service not fully implemented yet.")

# =========================================================================
# 7. CHAT ENDPOINT (Integrated Gemini Logic)
# =========================================================================
PREDEFINED_RESPONSES = {
    "pain": "If you experience pain during exercises, stop immediately. Sharp pain is a warning sign. Consult your healthcare provider if pain persists.",
    # ... (other responses)
}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        user_message = request.message
        session_id = request.session_id
        
        # --- 1. Check Predefined Keyword Responses First ---
        message_lower = user_message.lower()
        for keyword, response in PREDEFINED_RESPONSES.items():
            if keyword in message_lower:
                return {"response": response}

        # --- 2. Handle Gemini AI Conversation ---
        
        if session_id not in active_chats:
            system_instruction = ("You are a helpful and encouraging AI rehabilitation assistant. ...")
            chat_session = ai_client.chats.create(
                model=MODEL_NAME, 
                config=GenerateContentConfig(system_instruction=system_instruction)
            )
            active_chats[session_id] = chat_session
        else:
            chat_session = active_chats[session_id]

        gemini_response = chat_session.send_message(user_message)
        return {"response": gemini_response.text}

    except Exception as e:
        print(f"Error in /api/chat: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An AI or Server error occurred: {str(e)}")

# =========================================================================
# 8. MAIN EXECUTION
# =========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
