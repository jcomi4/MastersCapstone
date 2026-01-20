from canvasapi import Canvas

# --- HARDCODED CONFIG (FOR TESTING ONLY) ---
API_URL = "https://canvas.instructure.com"
API_KEY = "7~HK8X7rz4KWuE42m6aEW8fZeVzBuAhu49wBfU9va6RfhE2C2RzKmTA2BAhZ6VWwEV "

# Initialize connection
canvas = Canvas(API_URL, API_KEY)

def fetch_course_data():
    try:
        # Get all courses
        courses = canvas.get_courses()
        
        # We'll just look at the first course for this test
        course = courses[0]
        print(f"Connected to: {course.name}\n")

        # 1. FETCH QUIZZES
        print("--- QUIZZES ---")
        quizzes = course.get_quizzes()
        for quiz in quizzes:
            # Quiz points are often stored as 'points_possible'
            points = getattr(quiz, 'points_possible', 0)
            due = getattr(quiz, 'due_at', 'No Due Date')
            print(f"Quiz: {quiz.title} | Points: {points} | Due: {due}")

        # 2. FETCH ASSIGNMENTS (Standard homework/papers)
        print("\n--- ASSIGNMENTS ---")
        assignments = course.get_assignments()
        for assign in assignments:
            # Assignment points are also 'points_possible'
            print(f"Assign: {assign.name} | Points: {assign.points_possible} | Due: {assign.due_at}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_course_data()
