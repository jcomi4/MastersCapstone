import google.generativeai as genai
import google.api_core.exceptions
import time
import json
from datetime import datetime

GOOGLE_API_KEY = "AIzaSyAhr0BifuvGfiVyZNf859nH1JPthpmBE_k"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def preprocess_assignments(assignments):
    return sorted(assignments, key=lambda x: x["days_until_due"] if x["days_until_due"] is not None else 999)

def build_prompt(canvas_data, prefs):
    courses = canvas_data["courses"]
    all_assignments = []
    all_materials = []
    for c in courses:
        for a in c["assignments"]:
            all_assignments.append({
                "course": c["course_name"],
                "name": a.get("name"),
                "due": a.get("due"),
                "days_until_due": a.get("days_until_due"),
                "instructions": a.get("instructions", ""),
                "url": a.get("url")
            })
        for m in c.get("modules", []):
            for it in m.get("items", []):
                all_materials.append({
                    "course": c["course_name"],
                    "module": m.get("module_name"),
                    "title": it.get("title"),
                    "type": it.get("type"),
                    "url": it.get("url")
                })
    all_assignments = preprocess_assignments(all_assignments)
    busy_list = "\n".join([f"- {b['day']}: {b['start']} to {b['end']} ({b['title']})" for b in prefs["busy_blocks"]])
    available_slots = prefs.get("available_slots", {})
    include_weekends = prefs.get("include_weekends", True)
    time_pref = prefs.get("time_preference", "No preference")
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""
You are building a weekly study schedule for a student.

TODAY: {today}

ASSIGNMENTS (sorted by urgency):
{json.dumps(all_assignments, indent=2)}

COURSE MATERIALS (module items like pages/files/links):
{json.dumps(all_materials[:150], indent=2)}

FIXED BUSY TIMES (do NOT schedule during these):
{busy_list}

AVAILABLE STUDY SLOTS (you MUST schedule ONLY inside these time windows):
{json.dumps(available_slots, indent=2)}

USER PREFERENCES:
- Include weekends: {include_weekends}
- Preferred study time: {time_pref}

RULES:
- Schedule ONLY inside available slots.
- Max study time per day: {prefs['max_hours_daily']} hours.
- Each block should be 30–90 minutes.
- Be SPECIFIC and use course materials.
- Use assignment/material URLs as markdown links when helpful.
- Do NOT create any "TAKE:" or "SUBMIT:" tasks.

OUTPUT:
Return ONLY valid JSON:
{{
  "Monday": [{{"start":"...","end":"...","course":"...","task":"...","materials":["..."],"notes":"..."}}],
  "Tuesday": [...],
  ...
}}
"""
    return prompt

def rank_my_tasks(canvas_data, prefs):
    if "error" in canvas_data:
        return f"❌ Canvas Error: {canvas_data['error']}"
    prompt = build_prompt(canvas_data, prefs)
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            return response.text
        except google.api_core.exceptions.ResourceExhausted:
            if attempt < 2:
                time.sleep(5)
                continue
            return "⚠️ API quota reached. Please wait and try again."
        except Exception as e:
            return f"❌ AI Error: {str(e)}"