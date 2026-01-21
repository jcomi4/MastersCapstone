from canvasapi import Canvas
from brain import rank_my_tasks

# --- CONFIGURATION ---
CANVAS_URL = "https://canvas.instructure.com"
CANVAS_TOKEN = "7~HK8X7rz4KWuE42m6aEW8fZeVzBuAhu49wBfU9va6RfhE2C2RzKmTA2BAhZ6VWwEV "

# Initialize Canvas connection
canvas = Canvas(CANVAS_URL, CANVAS_TOKEN)

def run_planner():
    try:
        # 1. Get your course (grabs the first one in your list)
        courses = canvas.get_courses()
        course = courses[0]
        print(f"📡 Connected to Canvas Course: {course.name}")

        # 2. Gather Assignments and Quizzes
        to_do_data = []
        
        # Pull Assignments
        for a in course.get_assignments():
            to_do_data.append({
                "type": "Assignment",
                "name": a.name,
                "due": str(a.due_at) if a.due_at else "No Due Date",
                "points": getattr(a, 'points_possible', 0)
            })
            
        # Pull Quizzes
        for q in course.get_quizzes():
            to_do_data.append({
                "type": "Quiz",
                "name": q.title,
                "due": str(q.due_at) if q.due_at else "No Due Date",
                "points": getattr(q, 'points_possible', 0)
            })

        # 3. SAFETY CHECK: Is the list empty?
        if not to_do_data:
            print("⚠️ No data found! Please add an assignment to your Canvas Sandbox first.")
            return

        print(f"🔍 Found {len(to_do_data)} items. Sending to AI...")
        
        # 4. Send to the AI Brain
        priority_list = rank_my_tasks(to_do_data)
        
        print("\n" + "="*40)
        print("🎓 YOUR AI-POWERED STUDY PLAN")
        print("="*40)
        print(priority_list)

    except Exception as e:
        print(f"❌ Error in main.py: {e}")

if __name__ == "__main__":
    run_planner()