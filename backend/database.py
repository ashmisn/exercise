"""
database.py
Supabase helpers: lazy client init, save_session_record, get_progress_for_user.
"""

import os
import traceback
from datetime import datetime as dt
from typing import Dict, Any

from supabase import create_client, Client

SUPABASE_URL = os.environ.get("VITE_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("VITE_SUPABASE_ANON_KEY")

_supabase: Client | None = None

def get_supabase_client() -> Client:
    global _supabase
    if _supabase is not None:
        return _supabase
    if not SUPABASE_URL or not SUPABASE_KEY:
        # fallback placeholder client (avoid crash in local dev)
        _supabase = create_client("http://localhost", "fake_key")
    else:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

supabase = get_supabase_client()

def save_session_record(record: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resp = supabase.table("user_sessions").insert([record]).execute()
        if getattr(resp, "error", None):
            raise Exception(getattr(resp.error, "message", str(resp.error)))
        return {"ok": True}
    except Exception as e:
        traceback.print_exc()
        return {"ok": False, "error": str(e)}

def get_progress_for_user(user_id: str) -> Dict[str, Any]:
    try:
        resp = supabase.table("user_sessions") \
            .select("exercise_name, reps_completed, accuracy_score, created_at, session_date") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .execute()
        sessions = getattr(resp, "data", resp)
        if not sessions:
            return {"user_id": user_id, "total_sessions": 0, "total_reps": 0, "average_accuracy": 0.0, "streak_days": 0, "weekly_data": [{"day": d, "reps": 0, "accuracy": 0.0} for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]], "recent_sessions": []}

        total_sessions = len(sessions)
        total_reps = sum(s.get("reps_completed", 0) for s in sessions)
        average_accuracy = 0.0
        if total_reps > 0:
            average_accuracy = sum(s.get("reps_completed", 0) * s.get("accuracy_score", 0.0) for s in sessions) / total_reps

        recent = sessions[:5]
        weekly_map = {d: {"reps": 0, "accuracy_sum": 0.0, "count": 0} for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]}

        for s in sessions:
            try:
                created = s.get("created_at") or s.get("session_date")
                dt_obj = dt.fromisoformat(created)
                day = dt_obj.strftime("%a")
                if day in weekly_map:
                    weekly_map[day]["reps"] += s.get("reps_completed", 0)
                    weekly_map[day]["accuracy_sum"] += s.get("accuracy_score", 0.0)
                    weekly_map[day]["count"] += 1
            except Exception:
                continue

        weekly_data = []
        for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]:
            m = weekly_map[d]
            avg = round(m["accuracy_sum"] / m["count"], 1) if m["count"] > 0 else 0.0
            weekly_data.append({"day": d, "reps": m["reps"], "accuracy": avg})

        return {"user_id": user_id, "total_sessions": total_sessions, "total_reps": total_reps, "average_accuracy": round(average_accuracy, 1), "streak_days": 0, "weekly_data": weekly_data, "recent_sessions": [{"date": s.get("session_date"), "exercise": s.get("exercise_name"), "reps": s.get("reps_completed"), "accuracy": round(s.get("accuracy_score", 0.0), 1)} for s in recent]}
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}
