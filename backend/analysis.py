"""
analysis.py
All pose-detection + frame processing + rep-counting logic.
Public API:
 - analyze_frame_base64(frame_b64: str, exercise_name: str, previous_state: dict) -> dict
 - get_2d_landmarks(landmarks) -> list
 - calculate_accuracy(current_angle, min_range, max_range) -> float
"""

import base64
import time
import math
import traceback
from typing import Optional, Dict, Tuple, List, Any

import cv2
import numpy as np
import mediapipe as mp
from fastapi import HTTPException

# Initialize MediaPipe once
mp_pose = mp.solutions.pose
POSE = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Mediapipe landmark index map for convenience
LM = {
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14,
    "left_wrist": 15, "right_wrist": 16,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28
}

def calculate_angle_2d(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> float:
    ax, ay = a[0] - b[0], a[1] - b[1]
    cx, cy = c[0] - b[0], c[1] - b[1]
    dot = ax * cx + ay * cy
    mag_a = math.hypot(ax, ay)
    mag_c = math.hypot(cx, cy)
    if mag_a == 0 or mag_c == 0:
        return 0.0
    cos_angle = max(min(dot / (mag_a * mag_c), 1.0), -1.0)
    return math.degrees(math.acos(cos_angle))

def get_2d_landmarks(landmarks) -> List[Dict[str, float]]:
    out = []
    for lm in landmarks:
        out.append({"x": lm.x, "y": lm.y, "visibility": getattr(lm, "visibility", 1.0)})
    return out

def get_point(landmarks, name: str) -> Tuple[float, float]:
    idx = LM.get(name)
    if idx is None:
        return (0.0, 0.0)
    lm = landmarks[idx]
    return (lm.x, lm.y)

def get_best_side(landmarks) -> Optional[str]:
    try:
        left_vis = landmarks[LM["left_shoulder"]].visibility + landmarks[LM["left_hip"]].visibility
        right_vis = landmarks[LM["right_shoulder"]].visibility + landmarks[LM["right_hip"]].visibility
        return "left" if left_vis >= right_vis else "right"
    except Exception:
        return None

def calculate_accuracy(current_angle: float, min_range: float, max_range: float) -> float:
    if max_range <= min_range:
        return 0.0
    center = (min_range + max_range) / 2.0
    half_span = (max_range - min_range) / 2.0
    if half_span == 0:
        return 0.0
    score = 1.0 - (abs(current_angle - center) / half_span)
    score = max(0.0, min(1.0, score))
    return score * 100.0

# --- Analysis functions (return (angle, coords, feedback_list)) ---
def analyze_shoulder_flexion(landmarks, side: str):
    a = get_point(landmarks, f"{side}_hip")
    b = get_point(landmarks, f"{side}_shoulder")
    c = get_point(landmarks, f"{side}_elbow")
    angle = calculate_angle_2d(a, b, c)
    return angle, {"a": a, "b": b, "c": c}, []

def analyze_shoulder_abduction(landmarks, side: str):
    return analyze_shoulder_flexion(landmarks, side)

def analyze_shoulder_internal_rotation(landmarks, side: str):
    # fallback heuristic
    return analyze_shoulder_flexion(landmarks, side)

def analyze_elbow_flexion(landmarks, side: str):
    a = get_point(landmarks, f"{side}_shoulder")
    b = get_point(landmarks, f"{side}_elbow")
    c = get_point(landmarks, f"{side}_wrist")
    angle = calculate_angle_2d(a, b, c)
    return angle, {"a": a, "b": b, "c": c}, []

def analyze_elbow_extension(landmarks, side: str):
    return analyze_elbow_flexion(landmarks, side)

def analyze_knee_flexion(landmarks, side: str):
    a = get_point(landmarks, f"{side}_hip")
    b = get_point(landmarks, f"{side}_knee")
    c = get_point(landmarks, f"{side}_ankle")
    angle = calculate_angle_2d(a, b, c)
    return angle, {"a": a, "b": b, "c": c}, []

def analyze_ankle_dorsiflexion(landmarks, side: str):
    a = get_point(landmarks, f"{side}_knee")
    b = get_point(landmarks, f"{side}_ankle")
    c = (b[0], b[1] - 0.05)
    angle = calculate_angle_2d(a, b, c)
    return angle, {"a": a, "b": b, "c": c}, []

def analyze_wrist_flexion(landmarks, side: str):
    a = get_point(landmarks, f"{side}_elbow")
    b = get_point(landmarks, f"{side}_wrist")
    c = (b[0], b[1] - 0.05)
    angle = calculate_angle_2d(a, b, c)
    return angle, {"a": a, "b": b, "c": c}, []

ANALYSIS_MAP = {
    "shoulder flexion": analyze_shoulder_flexion,
    "shoulder abduction": analyze_shoulder_abduction,
    "shoulder internal rotation": analyze_shoulder_internal_rotation,
    "elbow flexion": analyze_elbow_flexion,
    "elbow extension": analyze_elbow_extension,
    "knee flexion": analyze_knee_flexion,
    "ankle dorsiflexion": analyze_ankle_dorsiflexion,
    "wrist flexion": analyze_wrist_flexion
}

# --- Top-level analyze function used by main.py ---
def analyze_frame_base64(frame_b64: str, exercise_name: str, previous_state: Optional[Dict[str, Any]] = None, exercise_configs: Dict = None) -> Dict:
    """
    Process a base64 encoded image and return the same response shape your monolith returned.
    - frame_b64: base64 string (with or without data URI prefix)
    - exercise_name: string key (lowercase)
    - previous_state: state dict from the client
    - exercise_configs: dictionary of configs (min/max/debounce/calibration_frames)
    """
    # Default handling
    DEFAULT_STATE = {"reps": 0, "stage": "down", "last_rep_time": 0, "dynamic_max_angle": 0, "dynamic_min_angle": 180, "frame_count": 0, "partial_rep_buffer": 0.0, "analysis_side": None}
    state = {**DEFAULT_STATE, **(previous_state or {})}
    reps = state["reps"]; stage = state["stage"]; last_rep_time = state["last_rep_time"]
    dynamic_max_angle = state["dynamic_max_angle"]; dynamic_min_angle = state["dynamic_min_angle"]
    frame_count = state["frame_count"]; partial_rep_buffer = state["partial_rep_buffer"]; analysis_side = state["analysis_side"]

    try:
        header, encoded = frame_b64.split(',', 1) if ',' in frame_b64 else ('', frame_b64)
        img_data = base64.b64decode(encoded)
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None or frame.size == 0:
            return {"reps": reps, "feedback": [{"type":"warning","message":"Video stream data corrupted."}], "accuracy_score": 0.0, "state": state, "drawing_landmarks": [], "current_angle": 0, "angle_coords": {}}

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = POSE.process(image_rgb)

        landmarks = None
        feedback = []
        angle = 0.0
        angle_coords = {}
        accuracy = 0.0

        if not results.pose_landmarks:
            feedback.append({"type":"warning","message":"No pose detected. Adjust camera view."})
        else:
            landmarks = results.pose_landmarks.landmark
            if analysis_side is None:
                analysis_side = get_best_side(landmarks)
            if analysis_side is None:
                feedback.append({"type":"warning","message":"Please turn sideways or expose one full side."})
            else:
                config = (exercise_configs or {}).get(exercise_name, {})
                if not config:
                    feedback.append({"type":"warning","message":f"Configuration not found for: {exercise_name}"})
                else:
                    analysis_func = ANALYSIS_MAP.get(exercise_name)
                    if not analysis_func:
                        feedback.append({"type":"warning","message":"Analysis function missing."})
                    else:
                        angle, angle_coords, analysis_feedback = analysis_func(landmarks, analysis_side)
                        feedback.extend(analysis_feedback)
                        if not analysis_feedback:
                            CALIBRATION_FRAMES = config.get('calibration_frames', 20)
                            DEBOUNCE_TIME = config.get('debounce', 1.5)
                            current_time = time.time()

                            if frame_count < CALIBRATION_FRAMES and reps == 0:
                                dynamic_max_angle = max(dynamic_max_angle, angle)
                                dynamic_min_angle = min(dynamic_min_angle, angle)
                                frame_count += 1
                                feedback.append({"type":"progress","message":f"Calibrating range ({frame_count}/{CALIBRATION_FRAMES}). Move fully from start to finish position."})
                                accuracy = 0.0

                            if frame_count >= CALIBRATION_FRAMES or reps > 0:
                                CALIBRATED_MIN_ANGLE, CALIBRATED_MAX_ANGLE = dynamic_min_angle, dynamic_max_angle
                                MIN_ANGLE_THRESHOLD_FULL = CALIBRATED_MIN_ANGLE + 5
                                MAX_ANGLE_THRESHOLD_FULL = CALIBRATED_MAX_ANGLE - 5
                                MIN_ANGLE_THRESHOLD_PARTIAL = CALIBRATED_MIN_ANGLE + 20
                                MAX_ANGLE_THRESHOLD_PARTIAL = CALIBRATED_MAX_ANGLE - 20
                                frame_accuracy = calculate_accuracy(angle, CALIBRATED_MIN_ANGLE, CALIBRATED_MAX_ANGLE)
                                accuracy = frame_accuracy

                                if angle < MIN_ANGLE_THRESHOLD_PARTIAL:
                                    stage = "up"
                                    feedback.append({"type":"instruction","message":"Hold contracted position at the top!" if angle < MIN_ANGLE_THRESHOLD_FULL else "Go deeper for a full rep."})

                                if angle > MAX_ANGLE_THRESHOLD_PARTIAL and stage == "up":
                                    if current_time - last_rep_time > DEBOUNCE_TIME:
                                        rep_amount = 0.0
                                        if angle > MAX_ANGLE_THRESHOLD_FULL:
                                            rep_amount, success_message = 1.0, "FULL Rep Completed! Well done."
                                        else:
                                            rep_amount, success_message = 0.5, "Partial Rep (50%) counted. Complete the movement."

                                        if rep_amount > 0:
                                            stage = "down"
                                            partial_rep_buffer = partial_rep_buffer + rep_amount
                                            last_rep_time = current_time
                                            if partial_rep_buffer >= 1.0:
                                                reps = reps + int(partial_rep_buffer)
                                                partial_rep_buffer = partial_rep_buffer % 1.0
                                            feedback.append({"type":"encouragement","message":f"{success_message} Total reps: {reps}"})
                                        else:
                                            feedback.append({"type":"warning","message":"Incomplete return to starting position."})
                                    else:
                                        feedback.append({"type":"warning","message":"Slow down! Ensure controlled return."})

                                if not any(f['type'] in ['warning','instruction','encouragement'] for f in feedback):
                                    if stage == 'up' and angle > MIN_ANGLE_THRESHOLD_FULL:
                                        feedback.append({"type":"progress","message":"Push further to the maximum range."})
                                    elif stage == 'down' and angle < MAX_ANGLE_THRESHOLD_FULL:
                                        feedback.append({"type":"progress","message":"Return fully to the starting position."})
                                    elif stage == 'down':
                                        feedback.append({"type":"progress","message":"Ready to start the next rep."})
                                    elif stage == 'up':
                                        feedback.append({"type":"progress","message":"Controlled movement upward."})

        final_accuracy_display = accuracy
        drawing_landmarks = get_2d_landmarks(landmarks) if landmarks else []
        new_state = {"reps": reps, "stage": stage, "angle": round(angle, 1), "last_rep_time": last_rep_time, "dynamic_max_angle": dynamic_max_angle, "dynamic_min_angle": dynamic_min_angle, "frame_count": frame_count, "partial_rep_buffer": partial_rep_buffer, "analysis_side": analysis_side}

        return {"reps": reps, "feedback": feedback if feedback else [{"type":"progress","message":"Processing..."}], "accuracy_score": round(final_accuracy_display, 2), "state": new_state, "drawing_landmarks": drawing_landmarks, "current_angle": round(angle, 1), "angle_coords": angle_coords, "min_angle": round(dynamic_min_angle,1), "max_angle": round(dynamic_max_angle,1), "side": analysis_side}

    except Exception as e:
        error_detail = str(e)
        if "Packet timestamp mismatch" in error_detail or "CalculatorGraph::Run() failed" in error_detail:
            raise HTTPException(status_code=400, detail="Transient analysis error. Please try again.")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Unexpected analysis error: {error_detail}")
