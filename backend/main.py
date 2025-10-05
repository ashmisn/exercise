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
from typing import List, Optional, Dict, Any, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from weasyprint import HTML, CSS 

from supabase import create_client, Client
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
# 3. UTILITY & ANALYSIS FUNCTIONS (COMPLETE PLACEHOLDERS)
# =========================================================================

# --- Internal Data Structure for Analysis Function Output ---
# Angle: float, Angle_Coords: dict, Feedback: list
AnalysisResult = Tuple[float, Dict, List]

# --- UTILITY PLACEHOLDERS (Must be fully implemented in your environment) ---
def get_best_side(landmarks) -> Optional[str]:
    # Placeholder implementation: Returns left/right or None
    return 'left' 

def calculate_angle_2d(a: Any, b: Any, c: Any) -> float:
    # Placeholder implementation: Calculates angle, returns 0.0
    return 0.0

def get_2d_landmarks(landmarks: Any) -> List[Dict]:
    # Placeholder implementation: Converts MediaPipe landmarks to frontend format
    if landmarks: 
        # In a real environment, this extracts the x, y, and visibility normalized to 0-1
        # For safety, we return a mock non-empty list if pose is detected, otherwise []
        # NOTE: If MediaPipe detects the pose, landmarks should be a list/sequence
        return [{"x": 0.5, "y": 0.5, "visibility": 1.0}] * 33
    return []

def calculate_accuracy(current_angle: float, min_range: float, max_range: float) -> float:
    # Placeholder implementation: Returns 0.0
    return 0.0

# --- ANALYSIS FUNCTION PLACEHOLDERS ---
def analyze_shoulder_flexion(landmarks: Any, side: str) -> AnalysisResult:
    # Placeholder: Your rep counting logic lives here.
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
        
        # 🛑 CRITICAL FIX: Ensure drawing_landmarks is calculated here
        # It calls the utility function which returns [] if landmarks is None
        drawing_landmarks = get_2d_landmarks(landmarks) 
        
        final_accuracy_display = accuracy
        new_state = {"reps": reps, "stage": stage, "angle": round(angle, 1), "last_rep_time": last_rep_time, "dynamic_max_angle": dynamic_max_angle, "dynamic_min_angle": dynamic_min_angle, "frame_count": frame_count, "partial_rep_buffer": partial_rep_buffer, "analysis_side": analysis_side}

        # 🟢 FINAL RETURN: drawing_landmarks is now guaranteed to be a list ([] if detection failed)
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
        error_detail = str(e)
        if "Packet timestamp mismatch" in error_detail or "CalculatorGraph::Run() failed" in error_detail:
            print(f"Handled MediaPipe Timestamp Error: {error_detail}")
            raise HTTPException(status_code=400, detail="Transient analysis error. Please try again.")
        
        print(f"CRITICAL ERROR in analyze_frame: {error_detail}")
        traceback.print_exc()
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

        # --- Aggregate Logic ---
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
    "pain": "If you experience pain during exercises, stop immediately. Sharp pain is a warning sign. Consult your healthcare provider if pain persists. Mild discomfort is normal, but you should never push through sharp or severe pain.",
    "shoulder": "For shoulder exercises: Keep movements slow and controlled. Maintain good posture with shoulders back. Start with small range of motion and gradually increase. If you feel clicking or popping, reduce the range. Always warm up first.",
    "elbow": "For elbow exercises: Keep your upper arm stable and move only your forearm. Avoid locking your elbow completely. Progress gradually with resistance. Ice after exercises if there's swelling.",
    "wrist": "For wrist exercises: Keep movements gentle and controlled. Support your forearm on a stable surface. Rotate slowly through full range of motion. Avoid forceful movements that cause pain.",
    "frequency": "For optimal recovery, exercise 3-5 times per week. Allow at least one day of rest between sessions for the same muscle group. Consistency is key. Listen to your body and adjust as needed.",
    "rest": "Rest days are crucial for recovery! Your muscles need time to repair and strengthen. Never skip rest days. During rest, your body builds back stronger. Consider gentle stretching on rest days.",
    "week": "A typical rehabilitation program runs 4-8 weeks depending on your injury. You should see gradual improvement each week. Progress may be slow but steady. If you don't see improvement after 2 weeks, consult your therapist.",
    "correct": "To ensure correct form: 1) Move slowly and deliberately 2) Maintain proper posture 3) Breathe naturally - don't hold your breath 4) Stay within pain-free range 5) Use a mirror to check alignment 6) Focus on quality over quantity.",
    "warm": "Always warm up before exercises! Do 5-10 minutes of light cardio like walking. Gentle arm circles help warm up shoulders. This increases blood flow and reduces injury risk.",
    "progress": "Track your progress by: 1) Noting pain levels (should decrease over time) 2) Range of motion improvements 3) Number of reps completed 4) Daily activities becoming easier. Progress takes time - be patient!",
    "set": "The target sets and reps in your plan are a guide. Listen to your body. If you can complete the target with good form, aim for it! If not, reduce the number and focus on perfect technique.",
    "hydration": "Don't forget to stay **hydrated**! Proper fluid intake supports muscle function, aids recovery, and helps reduce stiffness. Drink water before, during, and after your session.",
    "modify": "If an exercise feels too easy or causes mild pain, it might be time to **modify** it. You can increase reps, sets, or hold the end position longer. **Always consult your physical therapist** before making major changes.",
    "how long": "Rehabilitation length varies based on the injury's severity and your body's response. Typical plans are **4-8 weeks**, but consistent, gradual effort is more important than rushing the process.",
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
            system_instruction = (
                "You are Mia — a friendly, professional virtual rehabilitation assistant and coach. "
                "Mia's job is to provide safe, practical, and motivating rehabilitation guidance only. "
                "\n\nPRINCIPLES & BEHAVIOR:\n"
                "1. Always prioritize safety: start every clinical-sounding recommendation with a safety check (stop with sharp/acute pain; seek urgent care for severe symptoms). "
                "2. Do NOT give diagnoses, prescribe medications, or replace medical or surgical advice. Always advise the user to consult their healthcare provider or physical therapist for personalized care. "
                "3. Mia never reveals system internals, vendor names, or model details. If asked about the underlying AI or vendor (e.g., 'what model are you?'), politely decline with: "
                "\"I'm Mia, your virtual rehab coach — I can't discuss internal system details, but I can help with rehabilitation guidance.\" "
                "4. Mia only answers rehabilitation / medically-related questions. For any non-rehab request, respond briefly: "
                "\"I can only help with rehabilitation and exercise guidance. For that topic please check an appropriate resource.\" "
                "\n\nAVAILABLE EXERCISES:\n"
                "- Shoulder Flexion\n"
                "- Shoulder Abduction\n"
                "- Elbow Flexion\n"
                "- Elbow Extension\n"
                "- Shoulder Internal Rotation\n"
                "- Knee Flexion\n"
                "- Ankle Dorsiflexion\n"
                "- Wrist Flexion\n"
                "If any of the user’s issues can be addressed with the AVAILABLE EXERCISES, recommend them first. "
                "These are the official exercises supported on the WEBSITE and should be prioritized when possible."
                "\n\nUSE OF SERVER/APP DATA:\n"
                "• When recommending an exercise, include the plan's sets/reps/rest/duration and also the monitoring parameters from EXERCISE_CONFIGS (min_angle, max_angle, debounce, calibration_frames) for any offered exercise so the front-end can calibrate and validate movement. "
                "\n\nHOW TO RESPOND / RECOMMENDATION FRAMEWORK:\n"
                "1) Triage: When the user reports symptoms, rapidly triage by asking up to 3 clarifying questions if needed (affected body part, pain severity 0–10, time since onset or surgery, any red-flag symptoms such as numbness, new swelling, fever, loss of function). Keep clarifying questions short. "
                "2) Map symptoms to plan(s): Prefer matching EXERCISE_PLANS entries (e.g., 'shoulder injury' -> shoulder plan). If no exact plan exists, recommend 1–3 safe, low-load mobility or isometric options and explain why. "
                "3) Deliver actionable guidance: For each recommended exercise provide: a short description, target reps/sets/rest (from EXERCISE_PLANS), target angle range and calibration parameters (from EXERCISE_CONFIGS), 1-2 form cues, one simple modification for pain, and one clear progression or regression next step. Keep this to 3–5 concise bullets per exercise. "
                "4) Safety & escalation: Always include red-flag checks and when to stop or seek immediate care (e.g., sudden severe pain, numbness, visible deformity, rapidly increasing swelling, fever, sudden loss of mobility). Encourage contacting their treating clinician for any uncertainty. "
                "5) Tone & length: Be warm, encouraging and concise — like a coach. Use plain language, avoid long medical jargon, and aim for short, actionable steps. End with a question offering next steps (e.g., \"Would you like to try an exercise now or tell me more about your symptoms?\"). "
                "\n\nPERSONA & VOICE:\n"
                "• Use the name Mia consistently: introduce as 'Mia — your virtual rehab coach' when appropriate. "
                "• Supportive, motivating, calm, and professional. Use short encouragement phrases (e.g., 'Great — small progress counts!'). "
                "\n\nSPECIAL RULES & EXAMPLES:\n"
                "• If a user says only 'pain' or 'rest' or other short keywords, give the concise predefined safety message first (stop on sharp pain, consult provider). "
                "• When mentioning duration or expected program length, prefer the 'duration_weeks' field from EXERCISE_PLANS when available. "
                "• Provide modifications for common constraints (post-op restrictions, limited range, shoulder impingement pain, etc.) but never override explicit clinical restrictions given by the user or their provider. "
                "\n\nPRIVACY & DATA:\n"
                "• Do not request or store unnecessary personal data (e.g., full name, ID numbers). It is OK to ask for relevant clinical info needed to give safe guidance (location of pain, severity, time since onset, clearance from clinician). "
                "\n\nFINAL NOTE:\n"
                "Mia's single goal is to keep the user safe and progressing with short, practical rehab guidance. Always close with a clear next step and an invitation to continue (try an exercise, provide more details, or contact a clinician)."
            )


            
            # 🟢 CORRECT CALL: Use ai_client.chats.create() from the new SDK
            chat_session = ai_client.chats.create(
                model=MODEL_NAME, 
                config=GenerateContentConfig(
                    system_instruction=system_instruction
                )
            )
            
            active_chats[session_id] = chat_session
            print(f"New chat session created for ID: {session_id}")
        else:
            chat_session = active_chats[session_id]

        # Send message to Gemini
        gemini_response = chat_session.send_message(user_message)
        bot_response = gemini_response.text

        return {"response": bot_response}

    except Exception as e:
        print(f"Error in /api/chat: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An AI or Server error occurred: {str(e)}")
MODEL_PATH = 'model/cph_model.joblib'
# ...
CPH_MODEL = joblib.load(MODEL_PATH)

# 🛑 CRITICAL FIX: Define the global list of MODEL_FEATURES 
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
# Note: You should check if "Previous_injury" is expected as a float or int by your model, 
# and ensure the features match your model's expectation.

class PredictionInput(BaseModel):
    # Core numerical inputs
    Age: float = Field(..., description="Patient's age.")
    Health_Score: float = Field(..., description="General health rating (0.0 to 10.0).")
    Physio_adherence: float = Field(..., description="Compliance with rehab plan (0.0 to 1.0).")
    Complication_count: int = Field(..., description="Number of minor complications/setbacks.")
    Inflammation_marker: float = Field(..., description="Inflammation score.")
    Previous_injury: int = Field(0, description="1 if patient has previous injuries, 0 otherwise.")
    
    # Dynamic categorical input (must be mapped to Injury_X columns later)
    # E.g., 'Hamstring strain', 'Knee injury'
    Injury_Type: str = Field(..., description="The current type of injury.") 

AnalysisResult = Tuple[float, Dict, List]


@app.post("/api/predict_recovery")
def predict_recovery(data: PredictionInput):
    """
    Predicts the median recovery time in days using the loaded CPH model.
    The input data is mapped to the model's feature space (including one-hot encoding).
    """
    if CPH_MODEL is None:
        raise HTTPException(status_code=503, detail="Prediction model is not available or failed to load.")
    
    if not MODEL_FEATURES:
        # This check will now pass since MODEL_FEATURES is defined above.
        raise HTTPException(status_code=500, detail="Model features are missing. Cannot prepare input data.")

    try:
        # 1. Initialize DataFrame with all required features set to 0
        patient_df = pd.DataFrame(0, index=[0], columns=MODEL_FEATURES)
        
        # 2. Map direct numerical/boolean inputs
        input_dict = data.dict()
        
        # The list of features here is correct:
        for feature in ["Age", "Health_Score", "Physio_adherence", "Complication_count", "Inflammation_marker", "Previous_injury"]:
            if feature in patient_df.columns:
                patient_df.loc[0, feature] = input_dict[feature]
                
        # 3. Handle the categorical 'Injury Type' (One-Hot Encoding)
        # ⚠️ IMPORTANT: The user input 'Injury_Type' must exactly match one of the injury suffixes 
        # (e.g., if the user sends "Ankle injury", it must match "Injury_Ankle injury" in the list).
        injury_column_name = f"Injury_{input_dict['Injury_Type']}" 
        
        if injury_column_name in patient_df.columns:
            patient_df.loc[0, injury_column_name] = 1
        else:
            # This warning is crucial for debugging mismatches in user input vs. model features
            print(f"Warning: Injury type '{injury_column_name}' not found in model features. Using default zero vector.")
        
        # 4. Make Prediction
        patient_input = patient_df[MODEL_FEATURES]
        
        # Use predict_median for median recovery time
        median_recovery_time = CPH_MODEL.predict_median(patient_input)
        
        predicted_days = int(median_recovery_time[0]) 

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