import base64
import cv2
import numpy as np
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import mediapipe as mp
import json
import datetime
import traceback
import requests
from weasyprint import HTML, CSS
from datetime import datetime as dt
import os
# --- NEW IMPORTS FOR SUPABASE ---
from supabase import create_client, Client 
# --------------------------------

# =========================================================================
# 1. MEDIAPIPE & FASTAPI SETUP
# =========================================================================
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
min_detection_confidence=0.5,
min_tracking_confidence=0.5
)

app = FastAPI(title="AI Physiotherapy API")

# Configure CORS middleware
FRONTEND_ORIGIN = "https://exercise-frontend-tt5l.onrender.com"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SUPABASE CONFIGURATION (Replaces IN_MEMORY_DB) ---
# ⚠️ ACTION REQUIRED: Set these environment variables in your Render project settings!
SUPABASE_URL = os.environ.get("VITE_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("VITE_SUPABASE_ANON_KEY")


# Initialize Supabase client globally
try:
    if SUPABASE_URL == "YOUR_SUPABASE_URL_HERE" or SUPABASE_KEY == "YOUR_SUPABASE_KEY_HERE":
        print("⚠️ WARNING: Using placeholder Supabase credentials. Sessions will fail unless environment variables are set.")
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase client initialized.")
except Exception as e:
    print(f"CRITICAL SUPABASE INIT ERROR: {e}")
    # In a real app, you might want to stop startup if the DB connection fails
# ---------------------------------------------------------------------


# =========================================================================
# 2. DATA MODELS & CONFIGURATION (Unchanged)
# =========================================================================
class Landmark2D(BaseModel):
    x: float
    y: float
    visibility: float = 1.0

class FrameRequest(BaseModel):
    frame: str
    exercise_name: str
    previous_state: Dict | None = None

class AilmentRequest(BaseModel):
    ailment: str

class SessionData(BaseModel):
    # The SessionData model must align with your Supabase table columns
    user_id: str
    exercise_name: str
    reps_completed: int
    accuracy_score: float
    # Note: duration_seconds and feedback fields are likely needed in the final system,
    # but based on the provided data model, we'll stick to these four for now.


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
# 3. UTILITY FUNCTIONS (Unchanged)
# =========================================================================
def get_best_side(landmarks):
    left_vis = (landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].visibility + landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].visibility) / 2
    right_vis = (landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].visibility + landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].visibility) / 2
    if left_vis > right_vis and left_vis > 0.6: return "left"
    elif right_vis > 0.6: return "right"
    else: return None

def calculate_angle_2d(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    if np.all(a == b) or np.all(c == b): return 0.0
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0: angle = 360 - angle
    return angle

def get_2d_landmarks(landmarks):
    return [{"x": lm.x, "y": lm.y, "visibility": lm.visibility} for lm in landmarks]

def calculate_accuracy(current_angle: float, min_range: float, max_range: float) -> float:
    if min_range >= max_range: return 0.0
    TARGET_MIN, TARGET_MAX, BUFFER = min_range, max_range, 10
    if current_angle >= TARGET_MIN and current_angle <= TARGET_MAX: return 100.0
    deviation = max(TARGET_MIN - current_angle, current_angle - TARGET_MAX)
    if deviation > BUFFER: return 0.0
    score = 100 * (1 - (deviation / BUFFER))
    return max(0.0, min(100.0, score))

def get_landmark_indices(side: str):
    is_left = side == "left"
    return {"HIP": mp_pose.PoseLandmark.LEFT_HIP.value if is_left else mp_pose.PoseLandmark.RIGHT_HIP.value, "SHOULDER": mp_pose.PoseLandmark.LEFT_SHOULDER.value if is_left else mp_pose.PoseLandmark.RIGHT_SHOULDER.value, "ELBOW": mp_pose.PoseLandmark.LEFT_ELBOW.value if is_left else mp_pose.PoseLandmark.RIGHT_ELBOW.value, "WRIST": mp_pose.PoseLandmark.LEFT_WRIST.value if is_left else mp_pose.PoseLandmark.RIGHT_WRIST.value, "KNEE": mp_pose.PoseLandmark.LEFT_KNEE.value if is_left else mp_pose.PoseLandmark.RIGHT_KNEE.value, "ANKLE": mp_pose.PoseLandmark.LEFT_ANKLE.value if is_left else mp_pose.PoseLandmark.RIGHT_ANKLE.value, "FOOT_INDEX": mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value if is_left else mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value, "INDEX": mp_pose.PoseLandmark.LEFT_INDEX.value if is_left else mp_pose.PoseLandmark.RIGHT_INDEX.value,}

# =========================================================================
# 4. EXERCISE ANALYSIS FUNCTIONS (Unchanged)
# =========================================================================
def analyze_shoulder_flexion(landmarks, side: str):
    indices = get_landmark_indices(side)
    LM_HIP, LM_SHOULDER, LM_ELBOW = indices["HIP"], indices["SHOULDER"], indices["ELBOW"]
    if landmarks[LM_HIP].visibility < 0.5 or landmarks[LM_SHOULDER].visibility < 0.5 or landmarks[LM_ELBOW].visibility < 0.5: return 0, {}, [{"type": "warning", "message": f"Low visibility for {side} shoulder/hip/elbow."}]
    P_HIP, P_SHOULDER, P_ELBOW = [landmarks[LM_HIP].x, landmarks[LM_HIP].y], [landmarks[LM_SHOULDER].x, landmarks[LM_SHOULDER].y], [landmarks[LM_ELBOW].x, landmarks[LM_ELBOW].y]
    angle = calculate_angle_2d(P_HIP, P_SHOULDER, P_ELBOW)
    angle_coords = {"A": {"x": P_HIP[0], "y": P_HIP[1]}, "B": {"x": P_SHOULDER[0], "y": P_SHOULDER[1]}, "C": {"x": P_ELBOW[0], "y": P_ELBOW[1]},}
    return angle, angle_coords, []
def analyze_shoulder_abduction(landmarks, side: str): return analyze_shoulder_flexion(landmarks, side)
def analyze_shoulder_internal_rotation(landmarks, side: str):
    indices = get_landmark_indices(side)
    LM_HIP, LM_ELBOW, LM_WRIST = indices["HIP"], indices["ELBOW"], indices["WRIST"]
    if landmarks[LM_HIP].visibility < 0.5 or landmarks[LM_ELBOW].visibility < 0.5 or landmarks[LM_WRIST].visibility < 0.5: return 0, {}, [{"type": "warning", "message": f"Low visibility for {side} shoulder/elbow/wrist."}]
    P_HIP, P_ELBOW, P_WRIST = [landmarks[LM_HIP].x, landmarks[LM_HIP].y], [landmarks[LM_ELBOW].x, landmarks[LM_ELBOW].y], [landmarks[LM_WRIST].x, landmarks[LM_WRIST].y]
    angle = calculate_angle_2d(P_HIP, P_ELBOW, P_WRIST)
    angle_coords = {"A": {"x": P_HIP[0], "y": P_HIP[1]}, "B": {"x": P_ELBOW[0], "y": P_ELBOW[1]}, "C": {"x": P_WRIST[0], "y": P_WRIST[1]},}
    return angle, angle_coords, []
def analyze_elbow_flexion(landmarks, side: str):
    indices = get_landmark_indices(side)
    LM_SHOULDER, LM_ELBOW, LM_WRIST = indices["SHOULDER"], indices["ELBOW"], indices["WRIST"]
    if landmarks[LM_SHOULDER].visibility < 0.5 or landmarks[LM_ELBOW].visibility < 0.5 or landmarks[LM_WRIST].visibility < 0.5: return 0, {}, [{"type": "warning", "message": f"Low visibility for {side} elbow/wrist/shoulder."}]
    P_SHOULDER, P_ELBOW, P_WRIST = [landmarks[LM_SHOULDER].x, landmarks[LM_SHOULDER].y], [landmarks[LM_ELBOW].x, landmarks[LM_ELBOW].y], [landmarks[LM_WRIST].x, landmarks[LM_WRIST].y]
    angle = calculate_angle_2d(P_SHOULDER, P_ELBOW, P_WRIST)
    angle_coords = {"A": {"x": P_SHOULDER[0], "y": P_SHOULDER[1]}, "B": {"x": P_ELBOW[0], "y": P_ELBOW[1]}, "C": {"x": P_WRIST[0], "y": P_WRIST[1]},}
    return angle, angle_coords, []
def analyze_elbow_extension(landmarks, side: str): return analyze_elbow_flexion(landmarks, side)
def analyze_knee_flexion(landmarks, side: str):
    indices = get_landmark_indices(side)
    LM_HIP, LM_KNEE, LM_ANKLE = indices["HIP"], indices["KNEE"], indices["ANKLE"]
    if landmarks[LM_HIP].visibility < 0.5 or landmarks[LM_KNEE].visibility < 0.5 or landmarks[LM_ANKLE].visibility < 0.5: return 0, {}, [{"type": "warning", "message": f"Low visibility for {side} hip/knee/ankle."}]
    P_HIP, P_KNEE, P_ANKLE = [landmarks[LM_HIP].x, landmarks[LM_HIP].y], [landmarks[LM_KNEE].x, landmarks[LM_KNEE].y], [landmarks[LM_ANKLE].x, landmarks[LM_ANKLE].y]
    angle = calculate_angle_2d(P_HIP, P_KNEE, P_ANKLE)
    angle_coords = {"A": {"x": P_HIP[0], "y": P_HIP[1]}, "B": {"x": P_KNEE[0], "y": P_KNEE[1]}, "C": {"x": P_ANKLE[0], "y": P_ANKLE[1]},}
    return angle, angle_coords, []
def analyze_ankle_dorsiflexion(landmarks, side: str):
    indices = get_landmark_indices(side)
    LM_KNEE, LM_ANKLE, LM_FOOT = indices["KNEE"], indices["ANKLE"], indices["FOOT_INDEX"]
    if landmarks[LM_KNEE].visibility < 0.5 or landmarks[LM_ANKLE].visibility < 0.5 or landmarks[LM_FOOT].visibility < 0.5: return 0, {}, [{"type": "warning", "message": f"Low visibility for {side} knee/ankle/foot."}]
    P_KNEE, P_ANKLE, P_FOOT = [landmarks[LM_KNEE].x, landmarks[LM_KNEE].y], [landmarks[LM_ANKLE].x, landmarks[LM_ANKLE].y], [landmarks[LM_FOOT].x, landmarks[LM_FOOT].y]
    angle = calculate_angle_2d(P_KNEE, P_ANKLE, P_FOOT)
    angle_coords = {"A": {"x": P_KNEE[0], "y": P_KNEE[1]}, "B": {"x": P_ANKLE[0], "y": P_ANKLE[1]}, "C": {"x": P_FOOT[0], "y": P_FOOT[1]},}
    return angle, angle_coords, []
def analyze_wrist_flexion(landmarks, side: str):
    indices = get_landmark_indices(side)
    LM_ELBOW, LM_WRIST, LM_FINGER = indices["ELBOW"], indices["WRIST"], indices["INDEX"]
    if landmarks[LM_ELBOW].visibility < 0.5 or landmarks[LM_WRIST].visibility < 0.5 or landmarks[LM_FINGER].visibility < 0.5: return 0, {}, [{"type": "warning", "message": f"Low visibility for {side} elbow/wrist/finger."}]
    P_ELBOW, P_WRIST, P_FINGER = [landmarks[LM_ELBOW].x, landmarks[LM_ELBOW].y], [landmarks[LM_WRIST].x, landmarks[LM_WRIST].y], [landmarks[LM_FINGER].x, landmarks[LM_FINGER].y]
    angle = calculate_angle_2d(P_ELBOW, P_WRIST, P_FINGER)
    angle_coords = {"A": {"x": P_ELBOW[0], "y": P_ELBOW[1]}, "B": {"x": P_WRIST[0], "y": P_WRIST[1]}, "C": {"x": P_FINGER[0], "y": P_FINGER[1]},}
    return angle, angle_coords, []

ANALYSIS_MAP = {
    "shoulder flexion": analyze_shoulder_flexion, "shoulder abduction": analyze_shoulder_abduction,
    "shoulder internal rotation": analyze_shoulder_internal_rotation, "elbow flexion": analyze_elbow_flexion,
    "elbow extension": analyze_elbow_extension, "knee flexion": analyze_knee_flexion,
    "ankle dorsiflexion": analyze_ankle_dorsiflexion, "wrist flexion": analyze_wrist_flexion,
}

# =========================================================================
# 5. API ENDPOINTS
# =========================================================================
@app.get("/")
def root():
    return {"message": "AI Physiotherapy API is running", "status": "healthy"}

@app.post("/api/get_plan")
def get_exercise_plan(request: AilmentRequest):
    ailment = request.ailment.lower()
    if ailment in EXERCISE_PLANS: return EXERCISE_PLANS[ailment]
    available = list(EXERCISE_PLANS.keys())
    raise HTTPException(status_code=404, detail=f"Exercise plan not found for '{ailment}'. Available plans: {available}")

@app.post("/api/analyze_frame")
def analyze_frame(request: FrameRequest):
    # ⚠️ We must rely on the global 'pose' object for performance stability.
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
        
        final_accuracy_display = accuracy
        drawing_landmarks = get_2d_landmarks(landmarks) if landmarks else []
        new_state = {"reps": reps, "stage": stage, "angle": round(angle, 1), "last_rep_time": last_rep_time, "dynamic_max_angle": dynamic_max_angle, "dynamic_min_angle": dynamic_min_angle, "frame_count": frame_count, "partial_rep_buffer": partial_rep_buffer, "analysis_side": analysis_side}

        return {"reps": reps, "feedback": feedback if feedback else [{"type": "progress", "message": "Processing..."}], "accuracy_score": round(final_accuracy_display, 2), "state": new_state, "drawing_landmarks": drawing_landmarks, "current_angle": round(angle, 1), "angle_coords": angle_coords, "min_angle": round(dynamic_min_angle, 1), "max_angle": round(dynamic_max_angle, 1), "side": analysis_side}

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
    # 🚫 NO 'finally: pose.close()' because the 'pose' object is global
    
# ... (rest of the API endpoints remain unchanged)

# =========================================================================
# 6. API ENDPOINTS MODIFIED FOR SUPABASE
# =========================================================================

@app.post("/api/save_session")
async def save_session(data: SessionData):
    """Saves session data to the 'user_sessions' table in Supabase."""
    try:
        # Prepare data record, aligning column names to your Supabase schema (user_sessions)
        session_record = {
            "user_id": data.user_id,
            "exercise_name": data.exercise_name,
            "reps_completed": data.reps_completed,
            "accuracy_score": data.accuracy_score,
            # Supabase usually handles 'created_at' and 'session_date' (if date type) automatically,
            # but we explicitly pass them for reliability and to match the old progress logic.
            "session_date": dt.now().strftime("%Y-%m-%d"), 
        }

        # Insert into Supabase (Ensure your table name is correct: 'user_sessions' or 'user_sessions')
        response = supabase.table("user_sessions").insert([session_record]).execute()
        
        # Check for errors returned by the Supabase client
        if response.error:
            print(f"SUPABASE INSERT ERROR: {response.error.message}")
            raise HTTPException(
                status_code=500, 
                detail=f"Database insert failed. Check RLS policies or Foreign Key constraints. Error: {response.error.message}"
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
        # Fetch all relevant sessions for the user, ordering by creation time
        response = supabase.table("user_sessions")\
            .select("exercise_name, reps_completed, accuracy_score, created_at, session_date")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
            
        sessions = response.data
        
        # If no data is found, return the empty structure
        if not sessions: 
            return {"user_id": user_id, "total_sessions": 0, "total_reps": 0, "average_accuracy": 0.0, "streak_days": 0, "weekly_data": [{"day": day, "reps": 0, "accuracy": 0.0} for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]], "recent_sessions": []}

        # --- Aggregate Logic (Using fetched data) ---
        total_sessions = len(sessions)
        total_reps = sum(s['reps_completed'] for s in sessions)
        # Calculate weighted average accuracy
        average_accuracy = sum(s['reps_completed'] * s['accuracy_score'] for s in sessions) / total_reps if total_reps > 0 else 0.0

        recent_sessions = sessions[:5]

        weekly_map = {day: {"reps": 0, "accuracy_sum": 0, "count": 0} for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
        
        for session in sessions:
            try:
                # Use the 'created_at' timestamp (ISO format from Supabase) for day calculation
                date_obj = dt.fromisoformat(session['created_at']) 
                day_name = date_obj.strftime('%a')
                if day_name in weekly_map:
                    weekly_map[day_name]['reps'] += session['reps_completed']
                    weekly_map[day_name]['accuracy_sum'] += session['accuracy_score']
                    weekly_map[day_name]['count'] += 1
            except ValueError:
                # Skip session if timestamp parsing fails
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
            "streak_days": 0, # Requires more complex logic, left at 0 for now
            "weekly_data": weekly_data, 
            "recent_sessions": [{"date": s['session_date'], "exercise": s['exercise_name'], "reps": s['reps_completed'], "accuracy": round(s['accuracy_score'], 1)} for s in recent_sessions]
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Server error fetching progress: {str(e)}")


# =========================================================================
# 7. PDF REPORT GENERATION UTILITIES (Uses new get_progress)
# =========================================================================
# ... (PDF functions remain the same as they call the updated get_progress) ...

def weekly_activity_html(weekly_data):
    html = ""
    max_reps = max([d['reps'] for d in weekly_data] + [1])
    for day in weekly_data:
        width_percent = (day['reps'] / max_reps) * 100
        color = "#16a34a" if day['reps'] > 0 else "#d1d5db"
        html += f"""
        <div style="margin:5px 0;">
            <strong>{day['day']}:</strong>
            <div style="background:#e5e7eb; width:100%; height:12px; border-radius:6px; overflow:hidden;">
                <div style="width:{width_percent}%; height:12px; background:{color};"></div>
            </div>
            <span style="font-size:12px;">Reps: {day['reps']} | Acc: {day['accuracy']}%</span>
        </div>
        """
    return html


def generate_pdf_report(user_id: str):
    # Calls the UPDATED get_progress
    user_data = get_progress(user_id) 

    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                line-height: 1.6;
            }}
            h1 {{
                text-align: center;
                color: #1f2937;
            }}
            .summary {{
                margin-top: 20px;
                padding: 15px;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: #f9fafb;
            }}
            .sessions {{
                margin-top: 20px;
            }}
            .session-item {{
                border-bottom: 1px solid #e5e7eb;
                padding: 8px 0;
            }}
        </style>
    </head>
    <body>
        <h1>Physiotherapy Progress Report</h1>
        <h2>User: {user_id}</h2>

        <div class="summary">
            <p><strong>Total Sessions:</strong> {user_data['total_sessions']}</p>
            <p><strong>Total Reps:</strong> {user_data['total_reps']}</p>
            <p><strong>Average Accuracy:</strong> {user_data['average_accuracy']}%</p>
            <p><strong>Streak Days:</strong> {user_data['streak_days']}</p>
        </div>

        <h3>Weekly Activity</h3>
        {weekly_activity_html(user_data['weekly_data'])}

        <h3>Recent Sessions</h3>
        <div class="sessions">
    """

    for session in user_data['recent_sessions']:
        html_content += f"""
            <div class="session-item">
                <strong>{session['date']}</strong> - {session['exercise']} <br>
                Reps: {session['reps']} | Accuracy: {session['accuracy']}%
            </div>
        """

    html_content += """
        </div>
    </body>
    </html>
    """

    # Save PDF file
    filename = f"progress_report_{user_id}.pdf"
    HTML(string=html_content).write_pdf(filename, stylesheets=[CSS(string='@page { size: A4; margin: 1cm; }')])
    return filename


# =========================================================================
# 8. PDF REPORT API ENDPOINT (Unchanged)
# =========================================================================

@app.get("/api/pdf/{user_id}")
def download_progress_report(user_id: str):
    try:
        pdf_path = generate_pdf_report(user_id)
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="PDF generation failed.")
        return FileResponse(pdf_path, media_type="application/pdf", filename=f"{user_id}_progress_report.pdf")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating PDF report: {str(e)}")


# =========================================================================
# 9. CHAT ENDPOINT (Updated)
# =========================================================================
class ChatRequest(BaseModel):
    message: str  

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        message = request.message.lower()

        # Predefined keyword-based responses
        responses = {
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
            # --- NEW RESPONSES ---
            "set": "The target sets and reps in your plan are a guide. Listen to your body. If you can complete the target with good form, aim for it! If not, reduce the number and focus on perfect technique.",
            "hydration": "Don't forget to stay **hydrated**! Proper fluid intake supports muscle function, aids recovery, and helps reduce stiffness. Drink water before, during, and after your session.",
            "modify": "If an exercise feels too easy or causes mild pain, it might be time to **modify** it. You can increase reps, sets, or hold the end position longer. **Always consult your physical therapist** before making major changes.",
            "how long": "Rehabilitation length varies based on the injury's severity and your body's response. Typical plans are **4-8 weeks**, but consistent, gradual effort is more important than rushing the process.",
            # --- END NEW RESPONSES ---
        }

        # Check if the message contains any keyword
        for keyword, response in responses.items():
            if keyword in message:
                return {"response": response}

        # Default fallback response
        return {
            "response": "I'm here to help with your rehabilitation exercises! You can ask me about:\n\n• Exercise techniques (shoulder, elbow, wrist)\n• Pain management\n• Exercise frequency and rest days\n• Proper form and technique\n• Progress tracking\n• Warm-up routines\n• Sets and Reps\n• Hydration\n\nWhat would you like to know?"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# =========================================================================
# 10. MAIN EXECUTION (Unchanged)
# =========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)