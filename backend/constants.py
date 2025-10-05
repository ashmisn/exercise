# app/constants.py
"""
Central place for exercise configs, plans and canned chat responses.
Keeps main.py small and imports-safe.
"""

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
    "shoulder injury": {
        "ailment": "shoulder injury",
        "exercises": [
            {"name": "Shoulder Flexion", "description": "Raise your arm forward and up", "target_reps": 1, "sets": 1, "rest_seconds": 3},
            {"name": "Shoulder Abduction", "description": "Raise your arm out to the side", "target_reps": 12, "sets": 3, "rest_seconds": 30},
            {"name": "Shoulder Internal Rotation", "description": "Rotate arm inward, keeping elbow bent.", "target_reps": 10, "sets": 3, "rest_seconds": 30}
        ],
        "difficulty_level": "beginner",
        "duration_weeks": 6
    },
    "leg/knee injury": {
        "ailment": "leg/knee injury",
        "exercises": [
            {"name": "Knee Flexion", "description": "Slide your heel towards your hip.", "target_reps": 1, "sets": 1, "rest_seconds": 3},
            {"name": "Ankle Dorsiflexion", "description": "Pull your foot up toward your shin.", "target_reps": 15, "sets": 3, "rest_seconds": 30}
        ],
        "difficulty_level": "beginner",
        "duration_weeks": 6
    },
    "elbow injury": {
        "ailment": "elbow injury",
        "exercises": [
            {"name": "Elbow Flexion", "description": "Bend your elbow bringing hand toward shoulder", "target_reps": 1, "sets": 1, "rest_seconds": 3},
            {"name": "Elbow Extension", "description": "Straighten your elbow completely", "target_reps": 15, "sets": 3, "rest_seconds": 30}
        ],
        "difficulty_level": "beginner",
        "duration_weeks": 4
    },
    "wrist injury": {
        "ailment": "wrist injury",
        "exercises": [
            {"name": "Wrist Flexion", "description": "Bend your wrist forward and back.", "target_reps": 1, "sets": 1, "rest_seconds": 3}
        ],
        "difficulty_level": "beginner",
        "duration_weeks": 3
    }
}

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
    "how long": "Rehabilitation length varies based on the injury's severity and your body's response. Typical plans are **4-8 weeks**, but consistent, gradual effort is more important than rushing the process."
}
