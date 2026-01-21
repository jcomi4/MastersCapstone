from google import genai
import json

GEMINI_API_KEY = "AIzaSyC9X5jn7wCNd1V57Iwx5qFUcpYi1nNVYXY"
client = genai.Client(api_key=GEMINI_API_KEY)

def rank_my_tasks(task_list):
    # These are the most stable string names for the 2026 API
    # Note: 'gemini-1.5-flash' often needs the '-latest' or version suffix
    models_to_try = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-2.0-flash"]
    
    for model_name in models_to_try:
        try:
            print(f"🤖 Attempting to use {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=f"Rank these student tasks (if there is only one, suggest how to tackle the assignment): {json.dumps(task_list)}"
            )
            return response.text
        except Exception as e:
            # We print the error but keep trying the next model
            print(f"⚠️ {model_name} failed. Moving to next...")
            continue
            
    return "❌ All models currently locked. Your Google Billing verification is likely still processing."