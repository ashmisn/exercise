import requests
from weasyprint import HTML, CSS
from datetime import datetime

# ---------------- CONFIG ----------------
USER_ID = "default_test_user"  # Replace dynamically if needed
API_URL = f"https://exercise-7edj.onrender.com/api/progress/{USER_ID}"
PDF_FILENAME = f"mobility_report_{USER_ID}_{datetime.now().strftime('%Y%m%d')}.pdf"
# ----------------------------------------

# --- Fetch progress data ---
try:
    response = requests.get(API_URL)
    response.raise_for_status()
    data = response.json()
except Exception as e:
    print(f"Error fetching progress data: {e}")
    exit(1)

# --- Helper functions for HTML ---
def weekly_activity_html(weekly_data):
    html = ""
    max_reps = max([d['reps'] for d in weekly_data] + [1])
    for day in weekly_data:
        width_percent = (day['reps'] / max_reps) * 100
        if day['accuracy'] > 90:
            color = "#16a34a"  # green
        elif day['accuracy'] > 75:
            color = "#f59e0b"  # yellow/orange
        else:
            color = "#dc2626"  # red
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
        date_str = datetime.fromisoformat(s['date']).strftime("%Y-%m-%d %H:%M")
        html += f"""
        <div class="session-card" style="page-break-inside: avoid;">
            <div class="session-header">
                <strong>{s['exercise']}</strong> <span class="session-date">{date_str}</span>
            </div>
            <div class="session-stats">{s['reps']} reps | {s['accuracy']}% Accuracy</div>
        </div>
        """
    return html

# --- Build full HTML ---
html_content = f"""
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
<p style="text-align:center;"><strong>User ID:</strong> {data['user_id']} | <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

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
{'Your streak is incredible! Keep it up!' if data['streak_days']>5 else 'Focus on precision and consistency this week!'}
</div>

</body>
</html>
"""

# --- Generate PDF ---
HTML(string=html_content).write_pdf(PDF_FILENAME)
print(f"Multi-page PDF generated: {PDF_FILENAME}")
