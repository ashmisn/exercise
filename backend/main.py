import base64
import cv2
import numpy as np
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import mediapipe as mp
import json
import datetime
import traceback

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
    allow_origins=["*"], # Allows all origins for local development
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

class SessionData(BaseModel): # MODEL FOR SAVING RESULTS
    user_id: str
    exercise_name: str
    reps_completed: int
    accuracy_score: float

# Exercise settings
EXERCISE_CONFIGS = {
    "shoulder flexion": {
        "min_angle": 30, "max_angle": 170, "debounce": 1.5, "calibration_frames": 20
    },
    "shoulder abduction": {
        "min_angle": 30, "max_angle": 170, "debounce": 1.5, "calibration_frames": 20
    },
    "elbow flexion": {
        "min_angle": 40, "max_angle": 170, "debounce": 1.5, "calibration_frames": 20
    },
    "elbow extension": {
        "min_angle": 150, "max_angle": 180, "debounce": 1.5, "calibration_frames": 20
    },
    "shoulder internal rotation": {
        "min_angle": 40, "max_angle": 110, "debounce": 1.5, "calibration_frames": 20
    },
    "knee flexion": {
        "min_angle": 40, "max_angle": 170, "debounce": 1.5, "calibration_frames": 20
    },
    "ankle dorsiflexion": {
        "min_angle": 80, "max_angle": 110, "debounce": 1.5, "calibration_frames": 20
    },
    "wrist flexion": { 
        "min_angle": 60, "max_angle": 120, "debounce": 1.5, "calibration_frames": 20
    }
}

# Dummy Exercise Plans
EXERCISE_PLANS = {
    "shoulder injury": {
        "ailment": "shoulder injury",
        "exercises": [
            { "name": "Shoulder Flexion", "description": "Raise your arm forward and up", "target_reps": 12, "sets": 3, "rest_seconds": 30 },
            { "name": "Shoulder Abduction", "description": "Raise your arm out to the side", "target_reps": 12, "sets": 3, "rest_seconds": 30 },
            { "name": "Shoulder Internal Rotation", "description": "Rotate arm inward, keeping elbow bent.", "target_reps": 10, "sets": 3, "rest_seconds": 30 },
        ],
        "difficulty_level": "beginner",
        "duration_weeks": 6
    },
    "leg/knee injury": { 
        "ailment": "leg/knee injury",
        "exercises": [
            { "name": "Knee Flexion", "description": "Slide your heel towards your hip.", "target_reps": 15, "sets": 3, "rest_seconds": 30 },
            { "name": "Ankle Dorsiflexion", "description": "Pull your foot up toward your shin.", "target_reps": 15, "sets": 3, "rest_seconds": 30 },
        ],
        "difficulty_level": "beginner",
        "duration_weeks": 6
    },
    "elbow injury": {
        "ailment": "elbow injury",
        "exercises": [
            { "name": "Elbow Flexion", "description": "Bend your elbow bringing hand toward shoulder", "target_reps": 15, "sets": 3, "rest_seconds": 30 },
            { "name": "Elbow Extension", "description": "Straighten your elbow completely", "target_reps": 15, "sets": 3, "rest_seconds": 30 }
        ],
        "difficulty_level": "beginner",
        "duration_weeks": 4
    },
    "wrist injury": { 
        "ailment": "wrist injury",
        "exercises": [
            { "name": "Wrist Flexion", "description": "Bend your wrist forward and back.", "target_reps": 15, "sets": 3, "rest_seconds": 30 },
        ],
        "difficulty_level": "beginner",
        "duration_weeks": 3
    }
}

# =========================================================================
# 3. UTILITY FUNCTIONS
# =========================================================================

def get_best_side(landmarks):
    """Determines the best side (left or right) for analysis based on visibility."""
    # Key anchor points for determining side stability
    left_vis = (landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].visibility + 
                landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].visibility) / 2
    right_vis = (landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].visibility + 
                 landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].visibility) / 2
    
    if left_vis > right_vis and left_vis > 0.6:
        return "left"
    elif right_vis > 0.6:
        return "right"
    else:
        return None

def calculate_angle_2d(a, b, c):
    """Calculates angle between three 2D points (A-B-C) where B is the vertex."""
    a = np.array(a) 
    b = np.array(b)
    c = np.array(c) 

    if np.all(a == b) or np.all(c == b):
        return 0.0

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)

    if angle > 180.0:
        angle = 360 - angle

    return angle

def get_2d_landmarks(landmarks):
    """Extracts 2D normalized landmarks and visibility for frontend drawing."""
    return [
        {"x": lm.x, "y": lm.y, "visibility": lm.visibility}
        for lm in landmarks
    ]

def calculate_accuracy(current_angle: float, min_range: float, max_range: float) -> float:
    """Calculates accuracy (0-100) based on deviation from the calibrated range."""
    if min_range >= max_range:
        return 0.0
    
    TARGET_MIN = min_range
    TARGET_MAX = max_range
    BUFFER = 10 # Allow 10 degrees outside the target before hitting 0%
    
    if current_angle >= TARGET_MIN and current_angle <= TARGET_MAX:
        return 100.0
    
    deviation = 0
    if current_angle < TARGET_MIN:
        deviation = TARGET_MIN - current_angle
    elif current_angle > TARGET_MAX:
        deviation = current_angle - TARGET_MAX
        
    if deviation > BUFFER:
        return 0.0
    
    score = 100 * (1 - (deviation / BUFFER))
    
    return max(0.0, min(100.0, score))


# =========================================================================
# 4. EXERCISE ANALYSIS FUNCTIONS
# =========================================================================

def get_landmark_indices(side: str):
    """Helper to get the correct LEFT or RIGHT landmark prefix."""
    return mp_pose.PoseLandmark.LEFT if side == "left" else mp_pose.PoseLandmark.RIGHT

def analyze_shoulder_flexion(landmarks, side: str):
    prefix = get_landmark_indices(side)
    
    LM_HIP = prefix.HIP.value
    LM_SHOULDER = prefix.SHOULDER.value
    LM_ELBOW = prefix.ELBOW.value
    
    if landmarks[LM_HIP].visibility < 0.5 or landmarks[LM_SHOULDER].visibility < 0.5 or landmarks[LM_ELBOW].visibility < 0.5:
        return 0, {}, [{"type": "warning", "message": f"Low visibility for {side} shoulder/hip/elbow."}]

    P_HIP = [landmarks[LM_HIP].x, landmarks[LM_HIP].y]
    P_SHOULDER = [landmarks[LM_SHOULDER].x, landmarks[LM_SHOULDER].y]
    P_ELBOW = [landmarks[LM_ELBOW].x, landmarks[LM_ELBOW].y]

    angle = calculate_angle_2d(P_HIP, P_SHOULDER, P_ELBOW)
    
    angle_coords = {
        "A": {"x": P_HIP[0], "y": P_HIP[1]},
        "B": {"x": P_SHOULDER[0], "y": P_SHOULDER[1]}, 
        "C": {"x": P_ELBOW[0], "y": P_ELBOW[1]},
    }
    return angle, angle_coords, []

def analyze_shoulder_abduction(landmarks, side: str):
    return analyze_shoulder_flexion(landmarks, side)

def analyze_shoulder_internal_rotation(landmarks, side: str): 
    prefix = get_landmark_indices(side)
    
    LM_HIP = prefix.HIP.value
    LM_ELBOW = prefix.ELBOW.value
    LM_WRIST = prefix.WRIST.value
    
    if landmarks[LM_HIP].visibility < 0.5 or landmarks[LM_ELBOW].visibility < 0.5 or landmarks[LM_WRIST].visibility < 0.5:
        return 0, {}, [{"type": "warning", "message": f"Low visibility for {side} shoulder/elbow/wrist."}]

    P_HIP = [landmarks[LM_HIP].x, landmarks[LM_HIP].y]
    P_ELBOW = [landmarks[LM_ELBOW].x, landmarks[LM_ELBOW].y]
    P_WRIST = [landmarks[LM_WRIST].x, landmarks[LM_WRIST].y]

    angle = calculate_angle_2d(P_HIP, P_ELBOW, P_WRIST) 
    
    angle_coords = {
        "A": {"x": P_HIP[0], "y": P_HIP[1]},
        "B": {"x": P_ELBOW[0], "y": P_ELBOW[1]}, 
        "C": {"x": P_WRIST[0], "y": P_WRIST[1]},
    }
    return angle, angle_coords, []

def analyze_elbow_flexion(landmarks, side: str):
    prefix = get_landmark_indices(side)

    LM_SHOULDER = prefix.SHOULDER.value
    LM_ELBOW = prefix.ELBOW.value
    LM_WRIST = prefix.WRIST.value
    
    if landmarks[LM_SHOULDER].visibility < 0.5 or landmarks[LM_ELBOW].visibility < 0.5 or landmarks[LM_WRIST].visibility < 0.5:
        return 0, {}, [{"type": "warning", "message": f"Low visibility for {side} elbow/wrist/shoulder."}]

    P_SHOULDER = [landmarks[LM_SHOULDER].x, landmarks[LM_SHOULDER].y]
    P_ELBOW = [landmarks[LM_ELBOW].x, landmarks[LM_ELBOW].y]
    P_WRIST = [landmarks[LM_WRIST].x, landmarks[LM_WRIST].y]

    angle = calculate_angle_2d(P_SHOULDER, P_ELBOW, P_WRIST)
    
    angle_coords = {
        "A": {"x": P_SHOULDER[0], "y": P_SHOULDER[1]},
        "B": {"x": P_ELBOW[0], "y": P_ELBOW[1]}, 
        "C": {"x": P_WRIST[0], "y": P_WRIST[1]},
    }
    return angle, angle_coords, []

def analyze_elbow_extension(landmarks, side: str):
    return analyze_elbow_flexion(landmarks, side)

def analyze_knee_flexion(landmarks, side: str): 
    prefix = get_landmark_indices(side)

    LM_HIP = prefix.HIP.value
    LM_KNEE = prefix.KNEE.value
    LM_ANKLE = prefix.ANKLE.value
    
    if landmarks[LM_HIP].visibility < 0.5 or landmarks[LM_KNEE].visibility < 0.5 or landmarks[LM_ANKLE].visibility < 0.5:
        return 0, {}, [{"type": "warning", "message": f"Low visibility for {side} hip/knee/ankle."}]

    P_HIP = [landmarks[LM_HIP].x, landmarks[LM_HIP].y]
    P_KNEE = [landmarks[LM_KNEE].x, landmarks[LM_KNEE].y]
    P_ANKLE = [landmarks[LM_ANKLE].x, landmarks[LM_ANKLE].y]

    angle = calculate_angle_2d(P_HIP, P_KNEE, P_ANKLE)
    
    angle_coords = {
        "A": {"x": P_HIP[0], "y": P_HIP[1]},
        "B": {"x": P_KNEE[0], "y": P_KNEE[1]}, 
        "C": {"x": P_ANKLE[0], "y": P_ANKLE[1]},
    }
    return angle, angle_coords, []

def analyze_ankle_dorsiflexion(landmarks, side: str): 
    prefix = get_landmark_indices(side)

    LM_KNEE = prefix.KNEE.value
    LM_ANKLE = prefix.ANKLE.value
    LM_FOOT = prefix.FOOT_INDEX.value
    
    if landmarks[LM_KNEE].visibility < 0.5 or landmarks[LM_ANKLE].visibility < 0.5 or landmarks[LM_FOOT].visibility < 0.5:
        return 0, {}, [{"type": "warning", "message": f"Low visibility for {side} knee/ankle/foot."}]

    P_KNEE = [landmarks[LM_KNEE].x, landmarks[LM_KNEE].y]
    P_ANKLE = [landmarks[LM_ANKLE].x, landmarks[LM_ANKLE].y]
    P_FOOT = [landmarks[LM_FOOT].x, landmarks[LM_FOOT].y]

    angle = calculate_angle_2d(P_KNEE, P_ANKLE, P_FOOT) 
    
    angle_coords = {
        "A": {"x": P_KNEE[0], "y": P_KNEE[1]},
        "B": {"x": P_ANKLE[0], "y": P_ANKLE[1]}, 
        "C": {"x": P_FOOT[0], "y": P_FOOT[1]},
    }
    return angle, angle_coords, []

def analyze_wrist_flexion(landmarks, side: str): 
    prefix = get_landmark_indices(side)
    
    LM_ELBOW = prefix.ELBOW.value
    LM_WRIST = prefix.WRIST.value
    LM_FINGER = prefix.INDEX.value
    
    if landmarks[LM_ELBOW].visibility < 0.5 or landmarks[LM_WRIST].visibility < 0.5 or landmarks[LM_FINGER].visibility < 0.5:
        return 0, {}, [{"type": "warning", "message": f"Low visibility for {side} elbow/wrist/finger."}]

    P_ELBOW = [landmarks[LM_ELBOW].x, landmarks[LM_ELBOW].y]
    P_WRIST = [landmarks[LM_WRIST].x, landmarks[LM_WRIST].y]
    P_FINGER = [landmarks[LM_FINGER].x, landmarks[LM_FINGER].y]

    angle = calculate_angle_2d(P_ELBOW, P_WRIST, P_FINGER)
    
    angle_coords = {
        "A": {"x": P_ELBOW[0], "y": P_ELBOW[1]},
        "B": {"x": P_WRIST[0], "y": P_WRIST[1]}, 
        "C": {"x": P_FINGER[0], "y": P_FINGER[1]},
    }
    return angle, angle_coords, []

# Map exercise names to their analysis function
ANALYSIS_MAP = {
    "shoulder flexion": analyze_shoulder_flexion,
    "shoulder abduction": analyze_shoulder_abduction, 
    "shoulder internal rotation": analyze_shoulder_internal_rotation,
    "elbow flexion": analyze_elbow_flexion,
    "elbow extension": analyze_elbow_extension,
    "knee flexion": analyze_knee_flexion, 
    "ankle dorsiflexion": analyze_ankle_dorsiflexion,
    "wrist flexion": analyze_wrist_flexion,
}

# =========================================================================
# 5. API ENDPOINTS
# =========================================================================

@app.get("/")
def root():
    return {"message": "AI Physiotherapy API is running", "status": "healthy"}

@app.post("/api/get_plan")
def get_exercise_plan(request: AilmentRequest):
    """Returns the static exercise plan for a given ailment."""
    ailment = request.ailment.lower()
    if ailment in EXERCISE_PLANS:
        return EXERCISE_PLANS[ailment]
    
    available = list(EXERCISE_PLANS.keys())
    raise HTTPException(
        status_code=404,
        detail=f"Exercise plan not found for '{ailment}'. Available plans: {available}"
    )

@app.post("/api/analyze_frame")
def analyze_frame(request: FrameRequest):
    # Initialize failure values
    reps, stage, last_rep_time = 0, "down", 0
    angle, angle_coords = 0, {}
    feedback = []
    
    # --- State initialization and retrieval (CRITICAL) ---
    DEFAULT_STATE = {
        "reps": 0, "stage": "down", "last_rep_time": 0,
        "dynamic_max_angle": 0,
        "dynamic_min_angle": 180,
        "frame_count": 0,
        "partial_rep_buffer": 0.0,
        "analysis_side": None # Store the chosen side for consistency
    }
    current_state = request.previous_state or DEFAULT_STATE
    
    reps = current_state.get("reps", 0)
    stage = current_state.get("stage", "down")
    last_rep_time = current_state.get("last_rep_time", 0)
    dynamic_max_angle = current_state.get("dynamic_max_angle", 0)
    dynamic_min_angle = current_state.get("dynamic_min_angle", 180)
    frame_count = current_state.get("frame_count", 0)
    partial_rep_buffer = current_state.get("partial_rep_buffer", 0.0)
    analysis_side = current_state.get("analysis_side", None) # Get last used side

    # --- DEBUG LOGGING FOR INCOMING STATE ---
    print(f"INCOMING STATE: Reps={reps}, Stage={stage}, Frame={frame_count}, Min/Max={dynamic_min_angle:.1f}/{dynamic_max_angle:.1f}")
    # ----------------------------------------

    try:
        # 1. Decode Frame
        header, encoded = request.frame.split(',', 1) if ',' in request.frame else ('', request.frame)
        img_data = base64.b64decode(encoded)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None or frame.size == 0:
            return {
                "reps": reps, "feedback": [{"type": "warning", "message": "Video stream data corrupted."}],
                "accuracy_score": 0.0, "state": current_state, "drawing_landmarks": [],
                "current_angle": 0, "angle_coords": {}
            }

        # 2. Process with MediaPipe
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)
        
        # --- Handle No Pose Detected ---
        if not results.pose_landmarks:
            feedback.append({"type": "warning", "message": "No pose detected. Adjust camera view."})
            accuracy = 0.0
        else:
            landmarks = results.pose_landmarks.landmark
            exercise_name = request.exercise_name.lower()
            
            # --- SIDE DETECTION LOGIC (User's choice stored in analysis_side takes priority) ---
            if analysis_side is None:
                # If no side is chosen/passed, auto-detect the best side
                analysis_side = get_best_side(landmarks)
                
            if analysis_side is None:
                 feedback.append({"type": "warning", "message": "Please turn sideways or expose one full side."})
                 accuracy = 0.0
                 angle = 0
            else:
                 # Configuration Lookup
                 config = EXERCISE_CONFIGS.get(exercise_name, {})
                 
                 if not config:
                     feedback.append({"type": "warning", "message": f"Configuration not found for: {exercise_name}"})
                     accuracy = 0.0
                 else:
                     analysis_func = ANALYSIS_MAP.get(exercise_name)
                     
                     if analysis_func:
                         # Pass the determined side to the analysis function
                         angle, angle_coords, analysis_feedback = analysis_func(landmarks, analysis_side)
                         feedback.extend(analysis_feedback)
                     else:
                         feedback.append({"type": "warning", "message": "Analysis function missing."})
                         accuracy = 0.0
                     
                     # --- DYNAMIC CALIBRATION / ANGLE TRACKING ---
                     if not analysis_feedback: # Only run if landmarks are visible
                         
                         # Calibration Phase: Track range
                         if frame_count < config['calibration_frames'] and reps == 0:
                             dynamic_max_angle = max(dynamic_max_angle, angle)
                             dynamic_min_angle = min(dynamic_min_angle, angle)
                             frame_count += 1
                             
                             feedback.append({"type": "progress", "message": f"Calibrating range ({frame_count}/{config['calibration_frames']}). Move fully!"})
                             accuracy = 0.0 # Accuracy is 0 during calibration
                             
                         # Once calibrated (or if reps started)
                         if frame_count >= config['calibration_frames'] or reps > 0:
                             
                             # Calculate current frame's accuracy based on dynamic range
                             CALIBRATED_MIN_ANGLE = dynamic_min_angle
                             CALIBRATED_MAX_ANGLE = dynamic_max_angle
                             frame_accuracy = calculate_accuracy(angle, CALIBRATED_MIN_ANGLE, CALIBRATED_MAX_ANGLE)
                             accuracy = frame_accuracy 

                             # Set thresholds for rep counting using calibrated range + buffer
                             DEBOUNCE_TIME = config['debounce']
                             current_time = time.time()
                             
                             MIN_ANGLE_THRESHOLD_FULL = CALIBRATED_MIN_ANGLE + 5 
                             MAX_ANGLE_THRESHOLD_FULL = CALIBRATED_MAX_ANGLE - 5 
                             
                             MIN_ANGLE_THRESHOLD_PARTIAL = CALIBRATED_MIN_ANGLE + 20 
                             MAX_ANGLE_THRESHOLD_PARTIAL = CALIBRATED_MAX_ANGLE - 20 


                             # 1. Lift Detection: Force stage to 'up' as soon as MIN angle is hit.
                             if angle < MIN_ANGLE_THRESHOLD_PARTIAL: 
                                 stage = "up"
                                 feedback.append({"type": "instruction", "message": "Hold contracted position."})
                             
                             # 2. Return Detection (Rep Completion)
                             if angle > MAX_ANGLE_THRESHOLD_PARTIAL and stage == "up":
                                 
                                 if current_time - last_rep_time > DEBOUNCE_TIME:
                                     
                                     rep_amount = 0.0
                                     success_message = ""
                                     
                                     if angle > MAX_ANGLE_THRESHOLD_FULL:
                                         rep_amount = 1.0
                                         success_message = "FULL Rep Completed!"
                                     elif angle > MAX_ANGLE_THRESHOLD_PARTIAL:
                                         rep_amount = 0.5
                                         success_message = "Partial Rep (50%) counted."
                                         
                                     if rep_amount > 0:
                                         stage = "down"
                                         
                                         partial_rep_buffer += rep_amount
                                         
                                         if partial_rep_buffer >= 1.0:
                                             reps += int(partial_rep_buffer)
                                             partial_rep_buffer = partial_rep_buffer % 1.0 
                                         
                                         last_rep_time = current_time
                                         feedback.append({"type": "encouragement", "message": f"{success_message} Total reps: {reps}"})
                                         print(f"SUCCESS: REPS={reps}, PARTIAL={round(partial_rep_buffer, 2)}, ANGLE={round(angle, 1)}°")
                                         
                                     else:
                                         feedback.append({"type": "warning", "message": "Too fast or insufficient return depth."})
                                 
                                 else:
                                     feedback.append({"type": "warning", "message": "Too fast! Wait for the full return."})
                             
                             # Post-calibration generic feedback
                             if not any(f['type'] not in ['warning', 'instruction', 'encouragement'] for f in feedback):
                                 if stage == 'up' and angle < MIN_ANGLE_THRESHOLD_FULL:
                                     feedback.append({"type": "progress", "message": "Excellent depth."})
                                 elif stage == 'down' and angle > MAX_ANGLE_THRESHOLD_FULL:
                                     feedback.append({"type": "progress", "message": "Ready to start."})
                                 else:
                                     feedback.append({"type": "progress", "message": "Maintain controlled movement."})
                     
                     else: # Fallback if analysis_feedback was present (low visibility)
                         accuracy = 0.0 
                     
                     # --- DEBUG LOGGING FOR EVERY FRAME ---
                     print(f"DEBUG: Exercise={exercise_name}, ANGLE={round(angle, 1)}°, STAGE={stage}, ACCURACY={round(accuracy, 1)}%")
                     # ----------------------------------------


        # --- Prepare Output Data ---
        final_accuracy_display = accuracy 

        drawing_landmarks = get_2d_landmarks(landmarks) if results.pose_landmarks else []

        return {
            "reps": reps,
            "feedback": feedback if feedback else [{"type": "progress", "message": "Processing..."}],
            "accuracy_score": round(final_accuracy_display, 2), # Using the frame's calculated accuracy
            "state": {
                "reps": reps, "stage": stage, "angle": round(angle, 1), "last_rep_time": last_rep_time,
                "dynamic_max_angle": dynamic_max_angle,
                "dynamic_min_angle": dynamic_min_angle,
                "frame_count": frame_count,
                "partial_rep_buffer": partial_rep_buffer,
                "analysis_side": analysis_side # NEW: Return the chosen side
            },
            "drawing_landmarks": drawing_landmarks,
            "current_angle": round(angle, 1),
            "angle_coords": angle_coords
        }

    except Exception as e:
        print(f"CRITICAL ERROR in analyze_frame: {e}")
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"Unexpected server error during analysis: {str(e)}")

# -------------------------------------------------------------------------
# NEW ENDPOINT: SAVE SESSION DATA (Simulated DB Write)
# -------------------------------------------------------------------------

@app.post("/api/save_session")
def save_session(data: SessionData):
    """Saves the completed session data to the simulated in-memory DB."""
    if data.user_id not in IN_MEMORY_DB:
        IN_MEMORY_DB[data.user_id] = []
        
    session_record = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "exercise": data.exercise_name,
        "reps": data.reps_completed,
        "accuracy": data.accuracy_score
    }
    
    IN_MEMORY_DB[data.user_id].append(session_record)
    
    print(f"DB WRITE: Saved {data.reps_completed} reps for {data.user_id}")
    return {"message": "Session saved successfully"}


# -------------------------------------------------------------------------
# PROGRESS DATA (Real from Simulated DB)
# -------------------------------------------------------------------------

@app.get("/api/progress/{user_id}")
def get_progress(user_id: str):
    """Returns aggregated real progress data from the simulated in-memory DB."""
    sessions = IN_MEMORY_DB.get(user_id, [])
    
    if not sessions:
        # If no real data, return minimal data structure to prevent frontend crash
        today = datetime.date.today().strftime('%Y-%m-%d')
        
        return {
            "user_id": user_id,
            "total_sessions": 0,
            "total_reps": 0,
            "average_accuracy": 0.0,
            "streak_days": 0,
            "weekly_data": [{"day": day, "reps": 0, "accuracy": 0} for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]],
            "recent_sessions": [],
        }


    # --- Aggregation Logic for Real Data ---
    total_sessions = len(sessions)
    total_reps = sum(s['reps'] for s in sessions)
    
    # Calculate weighted average accuracy
    if total_reps > 0:
        total_weighted_accuracy = sum(s['reps'] * s['accuracy'] for s in sessions)
        average_accuracy = total_weighted_accuracy / total_reps
    else:
        average_accuracy = 0.0

    # Sort sessions by timestamp (most recent first)
    sessions.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_sessions = sessions[:5] # Get the top 5 recent sessions

    # Calculate weekly data (Simplified: aggregates total reps/accuracy per day of the week)
    weekly_map = {day: {"reps": 0, "accuracy_sum": 0, "count": 0} for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
    
    for session in sessions:
        try:
            date_obj = datetime.datetime.strptime(session['timestamp'].split(' ')[0], '%Y-%m-%d')
            day_name = date_obj.strftime('%a')
            
            if day_name in weekly_map:
                weekly_map[day_name]['reps'] += session['reps']
                weekly_map[day_name]['accuracy_sum'] += session['accuracy']
                weekly_map[day_name]['count'] += 1
        except ValueError:
            # Skip invalid dates
            continue

    weekly_data = []
    for day_name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        data = weekly_map[day_name]
        weekly_data.append({
            "day": day_name,
            "reps": data['reps'],
            "accuracy": round(data['accuracy_sum'] / data['count'], 1) if data['count'] > 0 else 0
        })

    # Note: Streak calculation is complex and requires full history, so we skip detailed logic for now.
    
    return {
        "user_id": user_id,
        "total_sessions": total_sessions,
        "total_reps": total_reps,
        "average_accuracy": round(average_accuracy, 1),
        "streak_days": 0, # Placeholder: Needs full Firestore history to calculate correctly
        "weekly_data": weekly_data,
        "recent_sessions": [
            { "date": s['timestamp'].split(' ')[0], "exercise": s['exercise'], "reps": s['reps'], "accuracy": round(s['accuracy'], 1) }
            for s in recent_sessions
        ]
    }

# =========================================================================
# 6. MAIN EXECUTION
# =========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
