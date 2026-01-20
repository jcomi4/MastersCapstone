from canvasapi import Canvas
from brain import rank_my_tasks  # This imports your AI function

API_URL = "https://canvas.instructure.com"
API_KEY = "YOUR_CANVAS_TOKEN"
canvas = Canvas(API_URL, API_KEY)

def run_planner():
    course = canvas.get_courses()[0]
    assignments = course.get_assignments()
    
    # Create a simplified list for the AI to read
    to_do_data = []
    for a in assignments:
        to_do_data.append({
            "name": a.name,
            "due": str(a.due_at),
            "points": a.points_possible
        })
    
    print("🧠 AI is thinking about your schedule...")
    priority_list = rank_my_tasks(to_do_data)
    
    print("\n--- YOUR PERSONALIZED PRIORITY LIST ---")
    print(priority_list)

if __name__ == "__main__":
    run_planner()
