from canvasapi import Canvas
import re

# --- CONFIGURATION ---
CANVAS_URL = "https://canvas.instructure.com"
CANVAS_TOKEN = "7~nuQaPTk3yKJDurHVhEv6XQ9xKeZcTRZzeKCf3XRmhEKJQryBXmxtMHZBrZGz6At9"

canvas = Canvas(CANVAS_URL, CANVAS_TOKEN)

def clean_html(raw_html):
    """Removes HTML tags from Canvas descriptions."""
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def get_canvas_data():
    """Fetches assignments and module items to return to the app."""
    try:
        courses = canvas.get_courses()
        course = courses[0] # Grabs your History of Rome course
        
        all_content = []

        # Pull Module Items
        modules = course.get_modules()
        for m in modules:
            items = m.get_module_items()
            for item in items:
                all_content.append({
                    "type": "Module Item",
                    "title": item.title,
                    "module": m.name
                })

        # Pull Detailed Assignments
        assignments = course.get_assignments()
        for a in assignments:
            all_content.append({
                "type": "Task",
                "name": a.name,
                "due": str(a.due_at) if a.due_at else "No Due Date",
                "instructions": clean_html(a.description)[:1500]
            })

        return all_content #

    except Exception as e:
        print(f"❌ Canvas Error: {e}")
        return []