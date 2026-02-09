import google.generativeai as genai
import google.api_core.exceptions
import time

# --- AI CONFIG ---
GOOGLE_API_KEY = "AIzaSyAhr0BifuvGfiVyZNf859nH1JPthpmBE_k"
genai.configure(api_key=GOOGLE_API_KEY)
# Using the stable model name
model = genai.GenerativeModel('gemini-2.0-flash')

def rank_my_tasks(content, prefs):
    busy_list = "\n".join([f"- {b['day']}: {b['start']} to {b['end']} ({b['title']})" for b in prefs['busy_blocks']])
    
    prompt = f"""
    You are an Academic Project Manager for a Master's student. 
    TASK CONTENT: {content}
    
    FIXED BUSY TIMES (DO NOT SCHEDULE STUDY DURING THESE):
    {busy_list}
    
    CONSTRAINTS:
    - Max study time per day: {prefs['max_hours_daily']} hours.
    - Format the schedule in a clean markdown table.
    - Use 12-hour AM/PM time for all suggestions.
    - Reference specific course modules from the data.
    """

    # Retry logic for Quota/API errors
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            return response.text
        except google.api_core.exceptions.ResourceExhausted:
            if attempt < 2:
                time.sleep(5) # Wait before retrying
                continue
            return "⚠️ API Quota hit. Please wait a minute and try again."
        except Exception as e:
            return f"❌ AI Error: {str(e)}"