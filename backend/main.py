import base64
import cv2
import numpy as np
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse # ADDED
from pydantic import BaseModel
from typing import List, Optional, Dict
import mediapipe as mp
import json
import datetime
import traceback
import requests
from weasyprint import HTML, CSS 
from datetime import datetime as dt 
import os # ADDED

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REALISM SIMULATION: IN-MEMORY DATABASE (Simulates persistence) ---
IN_MEMORY_DB = {} 
# ---------------------------------------------------------------------


# =========================================================================
# 2. DATA MODELS & CONFIGURATION
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
    user_id: str
    exercise_name: str
    reps_completed: int
    accuracy_score: float

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
    "shoulder injury": {"ailment": "shoulder injury", "exercises": [{ "name": "Shoulder Flexion", "description": "Raise your arm forward and up", "target_reps": 12, "sets": 3, "rest_seconds": 30 }, { "name": "Shoulder Abduction", "description": "Raise your arm out to the side", "target_reps": 12, "sets": 3, "rest_seconds": 30 }, { "name": "Shoulder Internal Rotation", "description": "Rotate arm inward, keeping elbow bent.", "target_reps": 10, "sets": 3, "rest_seconds": 30 }], "difficulty_level": "beginner", "duration_weeks": 6},
    "leg/knee injury": {"ailment": "leg/knee injury", "exercises": [{ "name": "Knee Flexion", "description": "Slide your heel towards your hip.", "target_reps": 15, "sets": 3, "rest_seconds": 30 }, { "name": "Ankle Dorsiflexion", "description": "Pull your foot up toward your shin.", "target_reps": 15, "sets": 3, "rest_seconds": 30 }], "difficulty_level": "beginner", "duration_weeks": 6},
    "elbow injury": {"ailment": "elbow injury", "exercises": [{ "name": "Elbow Flexion", "description": "Bend your elbow bringing hand toward shoulder", "target_reps": 15, "sets": 3, "rest_seconds": 30 }, { "name": "Elbow Extension", "description": "Straighten your elbow completely", "target_reps": 15, "sets": 3, "rest_seconds": 30 }], "difficulty_level": "beginner", "duration_weeks": 4},
    "wrist injury": {"ailment": "wrist injury", "exercises": [{ "name": "Wrist Flexion", "description": "Bend your wrist forward and back.", "target_reps": 15, "sets": 3, "rest_seconds": 30 }], "difficulty_level": "beginner", "duration_weeks": 3}
}

# =========================================================================
# 3. UTILITY FUNCTIONS (Condensed for brevity, assumed correct)
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
# 4. EXERCISE ANALYSIS FUNCTIONS (Condensed for brevity, assumed correct)
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
# 5. API ENDPOINTS (analyze_frame, save_session, get_progress - Unchanged logic)
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
    reps, stage, last_rep_time = 0, "down", 0
    angle, angle_coords, feedback, accuracy = 0, {}, [], 0.0
    DEFAULT_STATE = {"reps": 0, "stage": "down", "last_rep_time": 0, "dynamic_max_angle": 0, "dynamic_min_angle": 180, "frame_count": 0, "partial_rep_buffer": 0.0, "analysis_side": None}
    current_state = request.previous_state or DEFAULT_STATE
    reps, stage, last_rep_time = current_state.get("reps", 0), current_state.get("stage", "down"), current_state.get("last_rep_time", 0)
    dynamic_max_angle, dynamic_min_angle = current_state.get("dynamic_max_angle", 0), current_state.get("dynamic_min_angle", 180)
    frame_count, partial_rep_buffer = current_state.get("frame_count", 0), current_state.get("partial_rep_buffer", 0.0)
    analysis_side = current_state.get("analysis_side", None)

    try:
        header, encoded = request.frame.split(',', 1) if ',' in request.frame else ('', request.frame)
        img_data = base64.b64decode(encoded)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None or frame.size == 0: return {"reps": reps, "feedback": [{"type": "warning", "message": "Video stream data corrupted."}], "accuracy_score": 0.0, "state": current_state, "drawing_landmarks": [], "current_angle": 0, "angle_coords": {}}

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
        print(f"CRITICAL ERROR in analyze_frame: {e}")
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"Unexpected server error during analysis: {str(e)}")

@app.post("/api/save_session")
def save_session(data: SessionData):
    if data.user_id not in IN_MEMORY_DB: IN_MEMORY_DB[data.user_id] = []
    session_record = {"timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S"), "exercise": data.exercise_name, "reps": data.reps_completed, "accuracy": data.accuracy_score}
    IN_MEMORY_DB[data.user_id].append(session_record)
    print(f"DB WRITE: Saved {data.reps_completed} reps for user {data.user_id}")
    return {"message": "Session saved successfully"}

@app.get("/api/progress/{user_id}")
def get_progress(user_id: str):
    sessions = IN_MEMORY_DB.get(user_id, [])
    if not sessions: return {"user_id": user_id, "total_sessions": 0, "total_reps": 0, "average_accuracy": 0.0, "streak_days": 0, "weekly_data": [{"day": day, "reps": 0, "accuracy": 0.0} for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]], "recent_sessions": []}

    total_sessions, total_reps = len(sessions), sum(s['reps'] for s in sessions)
    average_accuracy = sum(s['reps'] * s['accuracy'] for s in sessions) / total_reps if total_reps > 0 else 0.0
    sessions.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_sessions = sessions[:5]

    weekly_map = {day: {"reps": 0, "accuracy_sum": 0, "count": 0} for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
    for session in sessions:
        try:
            date_part = session['timestamp'].split(' ')[0]
            date_obj = dt.strptime(date_part, '%Y-%m-%d')
            day_name = date_obj.strftime('%a')
            if day_name in weekly_map:
                weekly_map[day_name]['reps'] += session['reps']
                weekly_map[day_name]['accuracy_sum'] += session['accuracy']
                weekly_map[day_name]['count'] += 1
        except ValueError: continue

    weekly_data = []
    for day_name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        data = weekly_map[day_name]
        weekly_data.append({"day": day_name, "reps": data['reps'], "accuracy": round(data['accuracy_sum'] / data['count'], 1) if data['count'] > 0 else 0.0})

    return {"user_id": user_id, "total_sessions": total_sessions, "total_reps": total_reps, "average_accuracy": round(average_accuracy, 1), "streak_days": 0, "weekly_data": weekly_data, "recent_sessions": [{"date": s['timestamp'].split(' ')[0], "exercise": s['exercise'], "reps": s['reps'], "accuracy": round(s['accuracy'], 1)} for s in recent_sessions]}


# =========================================================================
# 6. PDF REPORT GENERATION UTILITIES
# =========================================================================

def weekly_activity_html(weekly_data):
    html = ""
    max_reps = max([d['reps'] for d in weekly_data] + [1]) 
    for day in weekly_data:
        width_percent = (day['reps'] / max_reps) * 100
        color = "#16a34a" if day['accuracy'] > 90 else ("#f59e0b" if day['accuracy'] > 75 else "#dc2626")
        html += f"""
        <div class="week-day" style="page-break-inside: avoid;">
            <div class="day-label">{day['day']}</div>
            <div class="bars">
                <div class="rep-bar" style="width:{width_percent}%;"></div>
                <div class="accuracy-bar" style="background:{color}; width:{day['accuracy']}%;"></div>
            </div>
            <div class="stats">{day['reps']} reps | {day['accuracy']}%</div>
        </div>
        """
    return html

def recent_sessions_html(sessions):
    html = ""
    for s in sessions:
        date_str = dt.fromisoformat(s['date']).strftime("%Y-%m-%d %H:%M") 
        html += f"""
        <div class="session-card" style="page-break-inside: avoid;">
            <div class="session-header">
                <strong>{s['exercise']}</strong> <span class="session-date">{date_str}</span>
            </div>
            <div class="session-stats">{s['reps']} reps | {s['accuracy']}% Accuracy</div>
        </div>
        """
    return html

def build_html_content(data):
    """Generates the full HTML content string for the PDF report."""
    return f"""
    <html>
    <head>
    <meta charset="UTF-8">
    <title>Mobility Recovery Report</title>
    <style>
    @page {{ size: A4; margin: 20mm; }}
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f0f4f8; }}
    h1 {{ text-align:center; color:#1e3a8a; }}
    h2 {{ color:#1e40af; margin-top: 30px; border-bottom:1px solid #ccc; padding-bottom:5px; page-break-after: avoid; }}
    .kpi-cards {{ display:flex; gap:10px; margin-bottom:30px; flex-wrap: wrap; }}
    .kpi-card {{
        flex:1; min-width:120px; background:white; padding:15px; border-radius:10px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        text-align:center; page-break-inside: avoid;
    }}
    .kpi-card .value {{ font-size:1.8em; font-weight:bold; }}
    .week-day {{ margin-bottom:15px; }}
    .day-label {{ font-weight:bold; }}
    .bars {{ position: relative; height:20px; margin:5px 0; background:#e5e7eb; border-radius:10px; }}
    .rep-bar {{ position:absolute; left:0; top:0; height:100%; background:#3b82f6; border-radius:10px 0 0 10px; }}
    .accuracy-bar {{ position:absolute; left:0; top:0; height:100%; border-radius:10px 0 0 10px; opacity:0.4; }}
    .stats {{ font-size:0.9em; color:#374151; }}
    .session-card {{ background:white; padding:10px; margin-bottom:10px; border-radius:8px; box-shadow:0 1px 4px rgba(0,0,0,0.1); page-break-inside: avoid; }}
    .session-header {{ font-weight:bold; display:flex; justify-content:space-between; }}
    .session-date {{ color:#6b7280; font-size:0.85em; }}
    .encouragement {{ background:#3b82f6; color:white; padding:15px; border-radius:10px; margin-top:20px; page-break-inside: avoid; }}
    </style>
    </head>
    <body>

    <h1>Mobility Recovery Report</h1>
    <p style="text-align:center;"><strong>User ID:</strong> {data['user_id']} | <strong>Generated:</strong> {dt.now().strftime('%Y-%m-%d %H:%M')}</p>

    <h2>Overall Stats</h2>
    <div class="kpi-cards">
        <div class="kpi-card">Total Sessions<div class="value">{data['total_sessions']}</div></div>
        <div class="kpi-card">Total Reps<div class="value">{data['total_reps']}</div></div>
        <div class="kpi-card">Average Accuracy<div class="value">{data['average_accuracy']:.1f}%</div></div>
        <div class="kpi-card">Streak Days<div class="value">{data['streak_days']}</div></div>
    </div>

    <h2>Weekly Activity</h2>
    {weekly_activity_html(data.get('weekly_data', []))}

    <h2>Recent Sessions</h2>
    {recent_sessions_html(data.get('recent_sessions', []))}

    <div class="encouragement">
    {'Your streak is incredible! Keep it up!' if data['streak_days'] > 5 else 'Focus on precision and consistency this week!'}
    </div>

    </body>
    </html>
    """

# -------------------------------------------------------------------------
# NEW ENDPOINT: DOWNLOAD PDF REPORT (FIX for 404 error)
# -------------------------------------------------------------------------

@app.get("/api/download_pdf/{user_id}")
async def download_pdf_report(user_id: str):
    """
    Fetches progress data by calling the get_progress endpoint internally, 
    generates a PDF report using WeasyPrint, and returns it for download.
    """
    # Create a unique filename for the temporary file
    PDF_FILENAME = f"mobility_report_{user_id}_{dt.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    try:
        # 1. Get aggregated data by calling the progress endpoint's function
        data = get_progress(user_id) 

        if data.get("total_sessions") == 0:
             raise HTTPException(status_code=404, detail="No session data found for this user to generate a report.")

        # 2. Generate PDF using WeasyPrint
        html_content = build_html_content(data)
        HTML(string=html_content).write_pdf(PDF_FILENAME)

        # 3. Return the file
        # Setting Content-Disposition header forces a file download
        headers = {'Content-Disposition': f'attachment; filename="{PDF_FILENAME}"'}
        print(f"File created successfully: {PDF_FILENAME}. Preparing to send...")
        
        return FileResponse(
            path=PDF_FILENAME, 
            media_type='application/pdf', 
            filename=PDF_FILENAME, 
            headers=headers
        )

    except HTTPException as e:
        # Re-raise explicit HTTP errors (like 404 from no data)
        raise e
    except Exception as e:
        # Log and raise a generic 500 error for unexpected failures (like WeasyPrint dependencies)
        print(f"Error generating or serving PDF: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF report. Check server logs for WeasyPrint system dependencies. Error: {str(e)}")
    
    finally:
        # 4. Cleanup: Delete the temporary file after it has been sent
        if os.path.exists(PDF_FILENAME):
             try:
                 os.remove(PDF_FILENAME)
                 print(f"Cleaned up temporary file: {PDF_FILENAME}")
             except Exception as e:
                 print(f"Warning: Failed to delete temporary file {PDF_FILENAME}. Error: {e}")


# =========================================================================
# 7. MAIN EXECUTION
# =========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
