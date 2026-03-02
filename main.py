from canvasapi import Canvas
import re
from datetime import datetime, timezone

CANVAS_URL = "https://canvas.instructure.com"
CANVAS_TOKEN = "7~WaQM9NJf9tKy6yCWZ3CBZQXkzLtwtf6MUEBQ6z4UTDZMzDuamJN9YD2nZMuKUVmW"

canvas = Canvas(CANVAS_URL, CANVAS_TOKEN)

def clean_html(raw_html):
    if not raw_html:
        return ""
    return re.sub(re.compile("<.*?>"), "", raw_html)

def api_url_to_web_url(url):
    if not url:
        return None
    if url.startswith(CANVAS_URL):
        return url.replace("/api/v1", "")
    return url

def list_active_courses():
    courses = list(canvas.get_courses(enrollment_state="active"))
    return [{"id": c.id, "name": c.name} for c in courses]

def _format_assignment(a, course_id):
    due_str = None
    days_until_due = None
    if a.due_at:
        try:
            due = datetime.fromisoformat(a.due_at.replace("Z", "+00:00"))
            due_str = due.strftime("%Y-%m-%d %I:%M %p")
            days_until_due = (due - datetime.now(timezone.utc)).days
        except Exception:
            due_str = str(a.due_at)
    html_url = getattr(a, "html_url", None)
    if not html_url:
        html_url = f"{CANVAS_URL}/courses/{course_id}/assignments/{a.id}"
    return {
        "name": a.name,
        "due": due_str,
        "days_until_due": days_until_due,
        "instructions": clean_html(a.description)[:800],
        "url": html_url,
    }

def get_canvas_data(course_ids):
    try:
        all_courses_data = []
        for cid in course_ids:
            course = canvas.get_course(cid)
            data = {
                "course_id": cid,
                "course_name": course.name,
                "assignments": [],
                "modules": []
            }
            for m in course.get_modules():
                module_entry = {"module_name": m.name, "items": []}
                try:
                    for item in m.get_module_items():
                        api_url = getattr(item, "url", None)
                        module_entry["items"].append({
                            "title": item.title,
                            "type": item.type,
                            "url": api_url_to_web_url(api_url)
                        })
                except Exception:
                    pass
                data["modules"].append(module_entry)
            for a in course.get_assignments():
                data["assignments"].append(_format_assignment(a, cid))
            all_courses_data.append(data)
        return {"courses": all_courses_data}
    except Exception as e:
        return {"error": str(e)}