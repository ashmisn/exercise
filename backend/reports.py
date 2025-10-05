"""
reports.py
WeasyPrint PDF generation using progress data from database.get_progress_for_user.
Returns path to generated PDF.
"""

import os
import tempfile
from weasyprint import HTML
from .database import get_progress_for_user

def weekly_activity_html(weekly_data):
    rows = ""
    for day in weekly_data:
        rows += f"<tr><td>{day['day']}</td><td>{day['reps']}</td><td>{day['accuracy']}</td></tr>"
    html = f"""
    <html>
    <head><meta charset="utf-8"/><style>
        body {{ font-family: Arial, sans-serif; padding: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        td, th {{ border: 1px solid #ddd; padding: 8px; }}
        th {{ background: #f4f4f4; }}
    </style></head>
    <body>
    <h1>Weekly Activity</h1>
    <table>
      <thead><tr><th>Day</th><th>Reps</th><th>Accuracy</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    </body>
    </html>
    """
    return html

def generate_pdf_report(user_id: str) -> str:
    data = get_progress_for_user(user_id)
    html = weekly_activity_html(data.get("weekly_data", []))
    tmpdir = tempfile.gettempdir()
    filename = f"mobility_report_{user_id}.pdf"
    filepath = os.path.join(tmpdir, filename)
    HTML(string=html).write_pdf(filepath)
    return filepath
